import os, sys
import struct
import random
import json
from stat import *
from manager.curvevolt import CurveVolt
from manager.curvevol import CurveVol
import manager.curveea as cea
from django.utils import timezone
from django.db import transaction
import manager.models as mmodels
import manager.forms as f
from django import forms
from django.urls import reverse
from django.template import loader
from django.http import JsonResponse
from django.http import HttpResponse
from django.http import HttpResponseRedirect

allowedExt = (
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


def ajax(request):
    if not request.method == 'POST':
        return JsonResponse({})
    command = request.POST.get('command', '')
    jsonData = {}
    print('cmd:', command)
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
            details = []
            for i,needD in enumerate(needsDescribe):
                details.append(None)
                if needD:
                    defails[-1] = {}
                    #TODO: process extra data ...
                    needed = ( 'ignoreRows', 'firstIsE', 'isSampling', 'voltMethod' )
                    for n in needed:
                        fieldname = ''.join(['f_', i, '_', n]);
                        fieldata = request.POST.get(fieldname, None) 
                        if fieldata is None:
                            if n == isSampling:
                                fieldata = False
                            elif n == firstIsE:
                                fieldata = False
                            isOk = False
                            break
                        details[-1][n] = fieldata
                    else:
                        #is OK
                        pass
            if isOk:
                #TODO: start parsing
                parseAndCreateModels(files=files, details=details)
                pass
            else:
                #TODO: return error
                pass
        else:
            #TODO: return error
            pass
    else:
        pass
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


def parseAndCreateModels(files, details):
    for f,d in zip(files,details):
        p = _parse(f, d)
        c = _createModel(p)
        if not c:
            raise 4

def _getParserClass(extension):
    ext = extension.lower()
    importlib = __import__('importlib')
    load_parser = importlib.import_module('manager.uploads.parsers.' + ext)
    extClass = ext[0:1].upper() + ext[1:]
    parser = getattr(load_parser, extClass)
    return parserClass

def _parse(cfile, details):
    ext = cfile.name.rsplit('.' ,1)[1]
    print('Attemping to parse %s -- extension is %s' % (cfile.__str__, ext))
    parserClass = _getParserClass(ext)
    parserObj = parserClass(cfile, defailt)
    return parserObj.parsedData


def _createModel(parsedData):
    pass


class UploadManager:
    _file_id = -1
    _curves = []
    _ufile = 0
    _fname = ""
    _fcomment = ""
    _user = None
    _analyte = ""
    _analyte_conc = ""
    _analyte_conc_list = []
    status = False

    data_format = {
        'file_path': None, #str
        'file_name': None, #str
        'file_comment': None, #str
        'method': None, #str, one of: LSV, SCV, NPV, DPV, SWV, CAM
        'stepTp': None, #float in ms
        'stepTw': None, #float in ms
        'pulseTp': None, #float in ms
        'pulseTw': None, #float in ms
        'nonaveragedsampling': None, #float - frequency in kHz 0 if not used
        'custom_params': None, #not required
        'curves': [
            {
                'curve_name': None, #str
                'curve_comment': None, #str
                'curve_potential': None, #list of float
                'curve_current': None, #list of float
                'curve_time': None, #list of float
                'sampling_data': None, #list of float - not required
            }
        ]
    }


    def __init__(self):
        pass

    def drawUpload(self, request, user):
        if ( request.method == 'POST' ):
            form = f.ExpUploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                temp_id = self.processTemp(user, request.FILES['file'])
                if ( temp_id >= 0 ):
                    return HttpResponseRedirect(
                        reverse('expUploadFinalize', args=[user.id, temp_id])
                    )
        else:
            form = f.ExpUploadFileForm()

        template = loader.get_template('manager/form.html')
        context = { 
            'user' : user, 
            'form': form, 
            'value': 'Next', 
            'name': 'uploadFile' 
        }
        return HttpResponse(template.render(context, request))

    def drawUploadFinalize(self, request, user, temp_id):
        class AddDetails(forms.Form):
            def __init__(self, model, *args, **kwargs):
                super(AddDetails, self).__init__(*args, **kwargs)
                for md in model.missingData:
                    self.addField(md, model)
                
            def addField(self, typename, model):
                if ( typename == 'file_name' ):
                    self.fields['file_name'] = forms.CharField(
                        max_length=128,
                        required=True, 
                        label='File name',
                        initial=model.fileName
                    )
                elif ( typename == 'file_comment' ):
                    self.fields['file_comment'] = forms.CharField(
                        max_length=256,
                        required=False, 
                        label='File comment',
                        initial=''
                    )
                else:
                    raise TypeError('Not implemented')

        temp = mmodels.TempFile.objects.get(id=temp_id)
        if not temp.canBeUpdatedBy(user):
            raise PermissionError('Not allowed')
        if ( request.method == 'POST'
        and not request.POST.get('addDetails', False) ):
            form = AddDetails(temp, request.POST)
        else:
            form = AddDetails(temp)

        template = loader.get_template('manager/form.html')
        context = {
            'user': user,
            'form': form,
            'value': 'Upload',
            'name': 'AddDetails'
        }
        return HttpResponse(template.render(context, request))


    def processTemp(self, user, uploaded_file):
        supported = { # file verification is done by full parse
            '.vol': self.checkVol,
            '.volt': self.checkVolt,
            '.voltc': self.checkVoltc,
            '.csv': self.checkCSV,
            '.xls': self.checkXLS,
            '.xlsx': self.checkXLS,
            '.txt': self.checkTXT
        }
        filename, file_extension = os.path.splitext(uploaded_file.name) 
        funCheckMissingData = supported.get(file_extension.lower(), None)
        if funCheckMissingData is None:
            raise TypeError('Unsupported file extension')
        missing_data = funCheckMissingData(uploaded_file.read()) #This may raise TypeError
        temp_id = self.uploadTemp(user, uploaded_file, missing_data)
        return temp_id

    def uploadTemp(self, user, uploaded_file, missing_data):
        temp = mmodels.TempFile(
            owner=user,
            uploadDate=timezone.now(),
            fileContents=uploaded_file.read(),
            fileName=uploaded_file.name,
            missingData=missing_data
        )
        temp.save()
        return temp.id

    def checkVol(self, fileContent):
        c = self.parseVol(fileContent=fileContent)
        if ( len(c) < 1 ):
            raise TypeError('Parsing error')
        return ['file_name', 'file_comment']

    def checkVolt(self, fileContent):
        c = self.parseVolt(fileContent=fileContent)
        if ( len(c) < 1 ):
            raise TypeError('Parsing error')
        return ['file_name', 'file_comment']

    def checkVoltc(self, fileContent):
        c = self.parseVoltc(fileContent=fileContent)
        if ( len(c) < 1 ):
            raise TypeError('Parsing error')
        return ['file_name', 'file_comment']

    def parseVol(self, fileContent):
        index = 0
        curvesNum = struct.unpack('<h', fileContent[index:index+2])[0]
        index += 2
        if ( __debug__ ):
            print("Number of curves in file: %i" % curvesNum)

        offsets = []
        names = []
        start_addr = 2 + (60*4) + (50*12) #num of curves (int16) + 60 params (int32[60]) + 50 curves names char[10] 
        if ( curvesNum > 0 and curvesNum <= 50 ):
            for i in range(0, curvesNum):
                name = str(struct.unpack('{}s'.format(10), fileContent[index:index+10])[0])
                index+=10 
                offset = struct.unpack('<h', fileContent[index:index+2])[0]
                index+=2
                names.append(name)
                offsets.append(offset)

        index = 2 + 50*12 # The dictionary of .vol always reseves the place for
                          # names and offsets of 50 curves
        params = struct.unpack('i'*60, fileContent[index:index+4*60])
        index += 4*60
        fileSize = len(fileContent)
        curves = []
        if ( len(offsets) > 0 ):
            for i, offset in enumerate(offsets):
                index_start = start_addr
                for a in range(0,i):
                    index_start += offsets[a]
                index_end = index_start + offsets[i]
                c = CurveVol(names[i],params)
                retIndex = c.unserialize(fileContent[index_start:index_end]) 
                curves.append(c)
                if (retIndex < (index_end-index_start)):
                    raise TypeError("WARNING!: last index lower than data end cyclic curve not processed ?")
        return curves

    def parseVoltc(self, fileContent):
        return self.parseVolt(fileContent=fileContent, isCompressed=True)

    def parseVolt(self, fileContent, isCompressed=False):
        index = 0
        curvesNum = struct.unpack('<i', fileContent[index:index+4])[0]
        index += 4
        if ( __debug__ ):
            print("Number of curves in file: %i" % curvesNum)

        curves = []
        for i in range(0, curvesNum):
            curveSize = struct.unpack('I', fileContent[index:index+4])[0]
            index+=4
            c = CurveVolt()
            c.unserialize(fileContent[index:index+curveSize], isCompressed) 
            curves.append(c)
            index+=curveSize-4 # 4 was added earlier
        return curves

    def checkTXT(self, fileContent):
        #TODO:
        import pandas as pd
        parsed = pd.read_table(self._ufile)

    def checkXLS(self, fileContent):
        #TODO:
        import pandas as pd
        parsed = pd.read_excel(self._ufile)

    def checkAutoLAB(self, fileContent):
        #TODO:
        pass

    def checkCSV(self, fileContent):
        pass

    @transaction.atomic 
    def process(self, user, ufile, name, comment):
        if not user:
            raise 3
        self._user = user
        self._fname = name
        self._fcomment = comment
        self._ufile = ufile

        if ( ufile.name.lower().endswith(".volt") or ufile.name.lower().endswith(".voltc") ):
            isCompressed = False
            if ( ufile.name.lower().endswith(".voltc") ):
                isCompressed = True
            self._parseVolt(isCompressed)
            sid=transaction.savepoint()
            try:
                self._createModels()
            except Exception as e:
                # doesnt matter what error it was, we need to rollback
                if ( __debug__ ):
                    print("Query failed, rolling back transaction. Exception: %s" % e)
                transaction.savepoint_rollback(sid)
                self.status = False
                return
            if ( __debug__ ):
                print("Query succesful, commiting.")
            transaction.savepoint_commit(sid)
            self.status = True
        
        elif ( ufile.name.lower().endswith(".vol") ):
            self._parseVol()
            sid=transaction.savepoint()
            try:
                self._createModels()
            except Exception as e:
                # doesnt matter what error it was, we need to rollback
                if ( __debug__ ):
                    print("Query failed, rolling back transaction. Exception: %s" % e)
                transaction.savepoint_rollback(sid)
                self.status = False
                return
            if ( __debug__ ):
                print("Query succesful, commiting.")
            transaction.savepoint_commit(sid)
            self.status = True
        
        else:
            if ( __debug__ ):
                print("Unknown extension")
    


    def _createModels(self):
        cf = CurveFile(
                owner=self._user, 
                name=self._fname,
                comment=self._fcomment,
                filename = self._ufile.name,
                fileDate=timezone.now(), 
                uploadDate=timezone.now() )
        cf.save()

        self._file_id = cf.id;

        order=0
        for c in self._curves:
            cb = Curve(        
                    curveFile=cf,    
                    orderInFile=order,  
                    name=c.name,  
                    comment=c.comment, 
                    params=c.vec_param, 
                    date=c.getDate() )
            cb.save()

#            if ( c.vec_param[Param.nonaveragedsampling] == 0 ):
#                pr = []
#            else:
#                pr = c.vec_probing
#
            pr = c.vec_probing
            cv = CurveData(
                    curve = cb, 
                    date = c.getDate(), 
                    processing = None,
                    time = c.vec_time, 
                    potential = c.vec_potential,
                    current = c.vec_current, 
                    probingData = pr )
            cv.save()

            ci = CurveIndex( 
                    curve = cb, 
                    potential_min = min(c.vec_potential), 
                    potential_max = max(c.vec_potential), 
                    potential_step = c.vec_potential[1] - c.vec_potential[0], 
                    time_min = min(c.vec_time), 
                    time_max = max(c.vec_time), 
                    time_step = c.vec_time[1] - c.vec_time[0], 
                    current_min = min(c.vec_current), 
                    current_max = max(c.vec_current), 
                    current_range = max(c.vec_current) - min(c.vec_current), 
                    probingRate = c.vec_param[Param.nonaveragedsampling] )
            ci.save()
            order+=1

    def _processAnalyte(self):
        if not self._analyte:
            raise 1
        if not self._analyte_conc:
            raise 2

        self._analyte_conc.replace(" ","")

        acl = self._analyte_conc.split(",")
        for conc in acl:
            self._analyte_conc_list.append(float(conc))

    def getFileId(self):
        return self._file_id


if __name__ == '__main__':
    p = Parse(sys.argv[1])
