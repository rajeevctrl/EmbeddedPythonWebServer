'''
Created on 13-Dec-2018

@author: rajeev
'''





from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
from cgi import parse_header, parse_multipart
from socketserver import ThreadingMixIn
import json
import inspect
from dateutil import _common
import numpy as np
import json
import logging

logger = logging.getLogger()

###################### Utility classes #######################
class _CommonUtil:
    def shuffle(self,lst):
        indicies = np.random.permutation(np.arange(lst[0].shape[0]))
        result = []
        for l in lst:
            l = l[indicies]
            result.append(l)
        return result
    
    def convertPlaceValuesToNpArray(self,placeValueList,num_rows,num_cols):
        """
        For given sparse values in form of dict, converts each dict to a row.
        """
        arr = [[0.0] * num_cols for x in range(num_rows)]
        arr = np.array(arr)
        for i,row in enumerate(placeValueList):
            for j,value in row.items():
                arr[int(i),int(j)] = float(value)                
        return arr
    
    def convertObjectToJson(self,obj):
        class NumPyJsonEncoder(json.JSONEncoder):
            def default(self, obj):
                """
                If object to be encoded is ndarray then convert to list and return list.
                If object to be encoded is class type then use its __dict__ and return __dict__.
                If object to be encoded is dict then use as it is and return as it is.
                """
                if isinstance(obj, np.ndarray):
                    return obj.tolist() # or map(int, obj)
                objDict = obj if type(obj).__name__ == "dict" else obj.__dict__
                #return json.JSONEncoder.default(self, objDict)     
                return objDict   
        jsonStr = json.dumps(obj, cls=NumPyJsonEncoder)
        return jsonStr
    
    def convertJsonToObject(self,jsonStr,cls):
        jsonDict = json.loads(jsonStr)
        #print(type(jsonDict).__name__,type(jsonDict[0]))
        if type(jsonDict).__name__ == 'dict' or type(jsonDict).__name__ == 'list' or type(jsonDict).__name__ == 'tuple':
            return jsonDict
        obj = cls(**jsonDict)
        return obj        


####################### Exposed classes ##################################

class ResponseEntity:
    status=None #int
    data=None # response data object
    headers=dict()
    #headers={
    #    "Content-type":"text/plain; charset=utf-8"
    #}    
    def __init__(self,status,data,headers=dict()):
        self.status = status
        self.data = data
        self.headers = headers
    
    
class RequestMapping:
    """
    Decorator class for Request mapping.
    """
    def __init__(self,path=None,produces="application/json"):
        self.path = path
        self.produces = produces
        #self.defaultAttributeValues = self.__dict__
        
    def __call__(self,func):
        return func
        


class EmbeddedServer:
    """
    This class creates an instance of embedded server.
    Constructor Parameters:
    ----------------------
    host:str --> Host name of server.
    
    port:int --> integer port number.
    
    restClassObjects:list --> A list of class objects that are supposed to act as rest classes.
        
    loggerMethRef: function --> Reference of method to be used as logging. Default is 'print()' method reference.
    
    """ 
    _urlMappings=dict()
    _logger = None
    
    def __init__(self,host,port,restClassObjects):
        """ Embedded server params."""
        self.host = host
        self.port = int(port)
        self.restClassObjects = restClassObjects
        logger.info("Searching classes {} for endpoint methods.".format(str([obj.__class__.__name__ for obj in self.restClassObjects])))       
        for classObj in self.restClassObjects:
            # Fetch all @RequestMapping methods of current class obj.
            path_meth_decorator = self.__getMethodNameWithRequestMappingAndPath(classObj, RequestMapping)            
            for path,methWithDecoratorValues in path_meth_decorator.items():
                EmbeddedServer._urlMappings[path] = methWithDecoratorValues
        logger.info("Loaded following URL mappings:")
        for path,methWithDecoratorValues in EmbeddedServer._urlMappings.items():
            logger.info("Mapped '{}' to {}".format(path,methWithDecoratorValues["methObj"]))
     
    
    def launchServer(self):
        """ Starts Embedded Server. """
        server_address = (self.host, self.port)
        httpServer = self._ThreadedServer(server_address, self._MessageHandler)
        try:
            logger.info("Starting server for Host:{} Port:{}".format(self.host,self.port))
            httpServer.serve_forever()
        except Exception as exp:
            logger.info("Error starting server for Host:{} Port:{}".format(self.host,self.port))
            logger.info(exp) 
        
    
    def __getMethodNameWithRequestMappingAndPath(self,classObj, decoratorCls):
        className = classObj.__class__
        defaultDecoratorAttrs = decoratorCls().__dict__
        decoratorName = decoratorCls.__name__
        sourcelines = inspect.getsourcelines(className)[0]
        result = dict()
        for i,line in enumerate(sourcelines):
            line = line.strip()
            if line.split('(')[0].strip() == '@'+decoratorName: # leaving a bit out
                i,line = self.__readMultilineDecorator(sourcelines, i)
                path = self.__extractPathFromDecorator(str(line.strip()))
                customDecoratorAttrs = self.__extractCustomAttrValuesDecorator(line)
                nextLine = sourcelines[i+1]
                name = nextLine.split('def')[1].split('(')[0].strip()
                attrValues = self.__combineDefaultAndCustomDecoratorAttrs(defaultDecoratorAttrs, customDecoratorAttrs)
                methWithDecorator={
                    "methObj":getattr(classObj,name),
                    "decoratorAttrValues":attrValues
                    }
                result[path] = methWithDecorator
        return result
                
    def __readMultilineDecorator(self,sourceLines,i):
        text = ""
        N = len(sourceLines)
        while i<N:
            line = sourceLines[i].strip()            
            if line.startswith("def "):
                i -= 1
                break
            else:
                line = self.__removeTrailingComment(line)
                text = text + line
            i += 1
        return i,text.strip()
            
    def __removeTrailingComment(self,line):
        text=""
        strStarted=None
        for i,c in enumerate(line):
            if (strStarted is None) and c=="#":
                break
            elif (strStarted is None) and (c!="'" and c!="\""):
                text = text + c
            elif (strStarted is None) and (c=="'" or c=="\""):
                strStarted=c
                text = text + c
            elif (strStarted is not None) and (c==strStarted):
                if c==strStarted and line[i-1]!="\\":
                    strStarted = None                
                text = text + c
            elif (strStarted is not None) and c=="#":
                text = text + c            
            else:
                text = text + c
        return text
            
             
    def __combineDefaultAndCustomDecoratorAttrs(self,defaultDict,customDict):
        """
        Populates custom values of attributes in default values.
        """
        finalValues = dict(defaultDict)
        for i,(key,value) in enumerate(defaultDict.items()):
            if key in customDict:
                value = customDict[key]
            if str(i) in customDict:
                value = customDict[str(i)]
            finalValues[key] = value
        return finalValues
    
       
    def __extractPathFromDecorator(self,strDecorator):
        attributes = strDecorator.strip().split("(")[1][:-1].split(",")
        path = None
        for i,attr in enumerate(attributes):
            if "=" in attr.strip():
                key,value = attr.strip().split("=")
                path = value if key=="path" else path
            elif i==0 and path is None:
                path=attr
        path = path.replace("'","").replace("\"","")
        return path
    
    def __extractCustomAttrValuesDecorator(self,strDecorator):
        """
        Extracts attribute values from actual decorator usage using '@'.
        """
        if "(" not in strDecorator:
            return dict()
        attribValues = strDecorator.strip().split("(")[1][:-1].split(",")
        attribValues = [val.strip().replace("'","").replace("\"","") for val in attribValues]
        attrs = dict()
        for i,attr in enumerate(attribValues):
            if "=" in attr:
                name,value = tuple([x.strip() for x in attr.split("=")])
                attrs[name] = value
            else:
                attrs[str(i)] = str(attr)
        return attrs

        
                
    class _ThreadedServer(ThreadingMixIn,HTTPServer):
        """
        _ThreadedServer class.
        """
        pass
    
    #class _ThreadedServer(HTTPServer):
    #    pass
            
    class _MessageHandler(BaseHTTPRequestHandler):
        _commonUtil = _CommonUtil()
        """
        _MessageHandler class.        """
        
        
        def do_POST1(self):
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            post_data = self.rfile.read(content_length) 
            logger.info("post_data:",post_data)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write("hello".encode())
        
        def do_POST(self):
            ctype, pdict = parse_header(self.headers['content-type'])
            length = int(self.headers['content-length'])
            if ctype == 'multipart/form-data':           
                postvars = parse_multipart(self.rfile, pdict)
                logger.info("multipart/form-data:",postvars)
                
            elif ctype == 'application/x-www-form-urlencoded':
                length = int(self.headers['content-length'])
                postvars = parse_qs(
                        self.rfile.read(length).decode(), 
                        keep_blank_values=1)
                #Unpack values of dict from list to string.
                postvars = dict((key,value[0]) for key,value in postvars.items())
                logger.info("application/x-www-form-urlencoded:",postvars)
                
            elif ctype == "application/json":
                length = int(self.headers['content-length'])
                postvars = json.loads(self.rfile.read(length).decode())
                logger.info("application/json:",postvars)
            logger.info("request: {}".format(self.request))
            logger.info("path: {}".format(self.path))
            
            # Extract attribute names of endpoint method and send only those attributes that are used in endpoint method.
            endpointMeth = EmbeddedServer._urlMappings[self.path]["methObj"]
            decoratorAttrValues = EmbeddedServer._urlMappings[self.path]["decoratorAttrValues"]
            endpointMethAttrs = inspect.getargspec(endpointMeth).args
            if endpointMethAttrs[0] == "self":
                endpointMethAttrs.remove(endpointMethAttrs[0])
            postvars = dict((key,value) for key,value in postvars.items() if key in endpointMethAttrs)
            responseEntity = endpointMeth(**postvars)
            
            # Send response.
            self.send_response(int(responseEntity.status))
            if responseEntity.headers is not None:
                for key,value in responseEntity.headers.items():
                    self.send_header(key,value)
            self.send_header('Content-type', decoratorAttrValues["produces"])
            self.end_headers()
            # Convert response object as per response encoding.
            respData = self.__formatResponseData(responseEntity.data,decoratorAttrValues["produces"])
            self.wfile.write(respData.encode())
            
        def __formatResponseData(self,dataObj,responseEncoding):
            respData = dataObj
            if responseEncoding == "application/json":
                respData = self._commonUtil.convertObjectToJson(respData)
            elif responseEncoding == "text/plain":
                respData = str(respData)
            return respData
    
        


    








    