import json
from django.utils.html import escape
from django.db import transaction
from django.urls import reverse
from django.http import JsonResponse
from django.db import DatabaseError
import manager.models as mmodels
from manager.helpers.decorators import with_user
from manager.exceptions import VoltPyFailed


allowedExt = (  # TODO: build based on parsers
    'vol',  # EAGraph
    'volt',  # EAPro,EAQt
    'voltc',  # EAQt (compressed volt)
    'txt',  # General
    'csv',  # General
    'ods',  # General: LO Calc
    'xls',  # General: MS Excel 
    'xlsx',  # General: MS Excel
)
"""
in preparation:
    'ici',  # Autolab, GPES: graphics/display (ignored)
    'ixi',  # Autolab, GPES: graphics/display (ignored)
    'iei',  # Autolab, GPES: graphics/display (ignored)
    'ocw',  # Autolab, GPES: signal data LSV/CVLSV (2 cols E, I)
    'oew',  # Autolab, GPES: signal data VOLT (2 cols E, I)
    'oxw',  # Autolab, GPES: signal data CHRONOPOT (2 cols ?)
    'icw',  # Autolab, GPES: parameters LSV/CVLSV
    'iew',  # Autolab, GPES: parameters VOLT
    'ixw',  # Autolab, GPES: parameters CHRONOPOT
)
"""

maxfile_size = 100000  # size in kB

listOfFields = {
    'ignoreRows': None,  # int
    'currentUnit': {
        'nA': [],
        'µA': [],
        'mA': [],
        'A': [],
    },
    'firstColumn': {
        'firstIsE': [
            'firstColumn_t',  # float
            'firstColumn_dE',  # float
        ],
        'firstIsT': [
            'firstColumn_Ep',  # float
            'firstColumn_Ek',  # float
            'firstColumn_dE',  # float
        ],
        'firstIsI': [
            'firstColumn_Ep',  # float
            'firstColumn_Ek',  # float
            'firstColumn_dE',  # float
            'firstColumn_t',  # float
        ],
    },
    'isSampling': {
        'on': [
            'isSampling_SPP',  # int Samples Per Point
            'isSampling_SFreq',  # float 
        ],
        None: []
    },
    'voltMethod': {
        'lsv': [],
        'scv': [],
        'npv': [],
        'dpv': [],
        'swv': [],
        'chonoamp': []
    }
}


@with_user
def ajax(request, user):
    """
    Handle ajax request for validation and file uploads.
    request has to be POST and have field .POST['command'].

    returns JsonResponse
    """
    if not request.method == 'POST':
        return JsonResponse({})
    if not user.groups.filter(name='registered_users').exists():
        return JsonResponse({})
    command = request.POST.get('command', '')
    jsonData = {}
    if command == 'filelist':
        filelist = request.POST.get('filelist', '')
        filelist = json.loads(filelist)
        (isOk, errors, needsDescribe) = verifyFileExt(filelist)
        jsonData = {'isOk': isOk, 'errors': errors, 'needsDescribe': needsDescribe}
    elif command == 'verify':
        pass
    elif command == 'allowedExt':
        jsonData = allowedExt
    elif command == 'upload':
        files = request.FILES.getlist('files[]')
        flist = []
        for f in files:
            flist.append({'name': f.name, 'size': f.size})
        isOk, errors, needsDescribe = verifyFileExt(flist)
        if isOk:
            details = {}
            errors = []
            details['fileset_name'] = escape(request.POST.get('fileset_name', ''))
            for i, needD in enumerate(needsDescribe):
                details[i] = {}
                if needD:
                    for f in listOfFields.keys():
                        fieldname = ''.join(['f_', str(i), '_', f])
                        fieldata = request.POST.get(fieldname, None)
                        details[i][f] = fieldata
                        if listOfFields[f] is not None:
                            try:
                                neededFields = listOfFields[f][fieldata]
                            except:
                                errors.append('Wrong field: %s.' % fieldata)
                                isOk = False
                                break

                            for nf in neededFields:
                                nfname = ''.join(['f_', str(i), '_', nf])
                                nfdata = request.POST.get(nfname, None)
                                if nfdata is None:
                                    isOk = False
                                    break
                                details[i][nf] = nfdata
                else:
                    #  No details are needed
                    pass
            if isOk:
                fileset_id = parseAndCreateModels(files=files, details=details, user=user)
                jsonData['command'] = 'success'
                jsonData['location'] = reverse('showFileset', args=[fileset_id])
            else:
                jsonData['command'] = 'failed'
                jsonData['errors'] = ''
                # TODO: log error
        else:
            jsonData['command'] = 'failed'
            jsonData['errors'] = 'Extension not verified'
    else:
        jsonData['command'] = 'failed'
        jsonData['errors'] = 'Error in POST'
        # TODO: log Unknown command
    return JsonResponse(jsonData)


def verifyFileExt(filelist):
    """
    Verify the file list:
        - are file parsable based on extensions
        - are any files required missing

    filelist -- list of file names

    returns tuple of 3 elements:
        isOk: True if no errors detected
        errors: list of errors in the order of filelist
        needsDescribe: T/F array, of which files requires
            additional info to be given by the user
    """
    isOk = True
    errors = []
    needsDescribe = []
    if len(filelist) == 0:
        isOk = False
    for f in filelist:
        errors.append(None)
        needsDescribe.append(False)
        if f['name'].endswith(('txt', 'xls', 'xlsx', 'csv', 'ods')):
            needsDescribe[-1] = True

        if not f['name'].endswith(allowedExt):
            isOk = False
            errors[-1] = 'Not allowed file type.'
        elif (f['size']/1000) > maxfile_size:
            errors[-1] = 'File too large. Max filesize is: %i kB' % maxfile_size
        elif f['name'].endswith(('icw', 'iew', 'ixw', 'ocw', 'oew', 'oxw')):
            # TODO: simplify
            fsplit = f['name'].rsplit('.', 1)
            fbase = fsplit[0]
            hasMatch = False
            for f2 in filelist:
                if f2 == f:
                    continue
                f2split = f2['name'].rsplit('.', 1)
                f2base = f2split[0]
                if f2base == fbase:
                    if fsplit[1].startswith('i'):
                        expectedext = 'o' + fsplit[1][1:]  # change from icw to ocw
                        if f2split[1] == expectedext:
                            hasMatch = True
                            break
                    elif fsplit[1].startswith('o'):
                        expectedext = 'i' + fsplit[1][1:]  # change from ocw to icw
                        if f2split[1] == expectedext:
                            hasMatch = True
                            break
            if not hasMatch:
                isOk = False
                fsplit = f['name'].rsplit('.', 1)
                ext2 = ''
                if fsplit[1].startswith('i'):
                    ext2 = 'o' + fsplit[1][1:]
                else:
                    ext2 = 'i' + fsplit[1][1:]
                errors[-1] = 'Please upload both file types: *.{t1} and *.{t2}'.format(
                    t1=fsplit[1],
                    t2=ext2
                )
    return isOk, errors, needsDescribe


@transaction.atomic
def parseAndCreateModels(files, details, user):
    """
    Try to load parser, create model and save to DB.
    returns the Fileset id
    """
    sid = transaction.savepoint()
    try:
        cf_ids = []
        for i, f in enumerate(files):
            d = details[i]
            cf_ids.append(_parseGetCFID(f, d, user))
        fsid = _saveFileset(cf_ids, user, details)
    except (DatabaseError, VoltPyFailed):
        transaction.savepoint_rollback(sid)
        raise
    transaction.savepoint_commit(sid)
    return fsid


def _saveFileset(cf_ids, user, details):
    """
    Save Fileset to DB connecting it to its
    curveFiles and return the Fileset id.
    """
    fs = mmodels.Fileset(
        owner=user,
        name=details.get('fileset_name', ''),
    )
    fs.save()
    for i in cf_ids:
        cf = mmodels.File.objects.get(id=i)
        fs.files.add(cf)
    fs.save()
    return fs.id


def _getParserClass(extension):
    """
    Get required parser class name based on
    the extension of the file.
    """
    ext = extension.lower()
    importlib = __import__('importlib')
    load_parser = importlib.import_module('manager.uploads.parsers.' + ext)
    extClass = ext[0:1].upper() + ext[1:]
    parser = getattr(load_parser, extClass)
    return parser


def _parseGetCFID(cfile, details, user):
    """
    Upload file and return File id.
    """
    ext = cfile.name.rsplit('.', 1)[1]
    parserClass = _getParserClass(ext)
    try:
        parserObj = parserClass(cfile, details)
        cf_id = parserObj.saveModels(user)
    except:
        raise VoltPyFailed('Could not parse file %s' % cfile.name)
    return cf_id
