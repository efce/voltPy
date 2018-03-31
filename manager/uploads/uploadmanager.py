import os, sys
import struct
import random
import json
#from stat import *
from django.utils import timezone
from django.utils.html import escape
from django.db import transaction
from django import forms
from django.urls import reverse
from django.template import loader
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.db import DatabaseError
import manager.models as mmodels
from manager.helpers.decorators import with_user

allowedExt = ( #build based on parsers ?
    'vol', #EAGraph
    'volt', #EAPro,EAQt
    'voltc', #EAQt (compressed volt)
    'txt',  #General
    'csv', #General
    'ods', #General: LO Calc
    'xls', #General: MS Excel 
    'xlsx', #General: MS Excel
    'ici', #Autolab, GPES: graphics/display (ignored)
    'ixi', #Autolab, GPES: graphics/display (ignored)
    'iei', #Autolab, GPES: graphics/display (ignored)
    'ocw', #Autolab, GPES: signal data LSV/CVLSV (2 cols E, I)
    'oew', #Autolab, GPES: signal data VOLT (2 cols E, I)
    'oxw', #Autolab, GPES: signal data CHRONOPOT (2 cols ?)
    'icw', #Autolab, GPES: parameters LSV/CVLSV
    'iew', #Autolab, GPES: parameters VOLT
    'ixw', #Autolab, GPES: parameters CHRONOPOT
)

maxfile_size = 100000 # size in kB

listOfFields = {
    'ignoreRows': None, # int 
    'currentUnit': {
        'nA': [],
        'µA': [],
        'mA': [],
        'A': [],
    },
    'firstColumn': {
        'firstIsE': [
            'firstColumn_t',# float
            'firstColumn_dE',# float
        ],
        'firstIsT': [
            'firstColumn_Ep', # float
            'firstColumn_Ek',# float
            'firstColumn_dE',# float
        ],
        'firstIsI': [
            'firstColumn_Ep', # float
            'firstColumn_Ek',# float
            'firstColumn_dE',# float
            'firstColumn_t',# float
        ],
    },
    'isSampling': {
        'on': [
            'isSampling_SPP', # int Samples Per Point
            'isSampling_SFreq', # float 
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
    if not request.method == 'POST':
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
            details['fileset_name'] = escape(request.POST.get('fileset_name', ''))
            for i,needD in enumerate(needsDescribe):
                details[i] = {}
                if needD:
                    for f in listOfFields.keys():
                        fieldname = ''.join(['f_', str(i), '_', f]);
                        fieldata = request.POST.get(fieldname, None) 
                        details[i][f] = fieldata
                        if listOfFields[f] != None:
                            try:
                                neededFields = listOfFields[f][fieldata]
                            except:
                                isOk = False
                                break

                            for nf in neededFields:
                                nfname = ''.join(['f_', str(i), '_', nf]);
                                nfdata = request.POST.get(nfname, None) 
                                if nfdata == None:
                                    isOk = False
                                    break
                                details[i][nf] = nfdata
                else:
                    #is OK
                    pass
            if isOk:
                #TODO: start parsing
                fileset_id = parseAndCreateModels(files=files, details=details, user=user)
                jsonData['command'] = 'success'
                jsonData['location'] = reverse('showFileSet', args=[fileset_id])
            else:
                jsonData['command'] = 'failed'
                raise 91
                #TODO: return error
                pass
        else:
            jsonData['command'] = 'failed'
            jsonData['errors'] = 'Extension not verified'
    else:
        raise TypeError('Unknown commnad.')
    return JsonResponse(jsonData)


def verifyFileExt(filelist):
    isOk = True
    errors = []
    needsDescribe = []
    if len(filelist) == 0:
        isOk = False
    for f in filelist:
        errors.append(None)
        needsDescribe.append(False)
        if f['name'].endswith( ('txt', 'xls', 'xlsx', 'csv', 'ods') ):
            needsDescribe[-1] = True

        if not f['name'].endswith(allowedExt):
            isOk = False
            errors[-1] = 'Not allowed file type.'
        elif (f['size']/1000) > maxfile_size:
            errors[-1] = 'File too large. Max filesize is: %i kB' % maxfile_size
        elif f['name'].endswith( ('icw', 'iew', 'ixw', 'ocw', 'oew', 'oxw') ):
            #TODO: simplify
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
                        expectedext = 'o' + fsplit[1][1:] #change from icw to ocw
                        if f2split[1] == expectedext:
                            hasMatch = True
                            break
                    elif fsplit[1].startswith('o'):
                        expectedext = 'i' + fsplit[1][1:] #change from ocw to icw
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
    sid=transaction.savepoint()
    try:
        cf_ids = []
        for i,f in enumerate(files):
            d = details[i]
            cf_ids.append(_parseGetCFID(f, d, user))
        fsid = _saveFileSet(cf_ids, user, details)
    except DatabaseError:
        transaction.savepoint_rollback(sid)
        return -1
    transaction.savepoint_commit(sid)
    return fsid

def _saveFileSet(cf_ids, user, details):
    fs = mmodels.FileSet(
        owner=user,
        name=details.get('fileset_name',''),
    )
    fs.save()
    for i in cf_ids:
        cf = mmodels.CurveFile.objects.get(id=i)
        fs.files.add(cf)
    fs.save()
    return fs.id


def _getParserClass(extension):
    ext = extension.lower()
    importlib = __import__('importlib')
    load_parser = importlib.import_module('manager.uploads.parsers.' + ext)
    extClass = ext[0:1].upper() + ext[1:]
    parser = getattr(load_parser, extClass)
    return parser

def _parseGetCFID(cfile, details, user):
    ext = cfile.name.rsplit('.' ,1)[1]
    parserClass = _getParserClass(ext)
    parserObj = parserClass(cfile, details)
    cf_id = parserObj.saveModels(user)
    return cf_id

if __name__ == '__main__':
    p = Parse(sys.argv[1])
