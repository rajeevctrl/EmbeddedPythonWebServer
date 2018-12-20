from embedded_server import ResponseEntity, RequestMapping, EmbeddedServer

class MyRest:
    
    @RequestMapping(path="/meth1",produces="application/json")
    def method1(self,param1,param2):
        print("param1 is:",param1)
        print("param2 is:",param2)
        responseData={
            "a":"hello",
            "b":"world"
            }
        response = ResponseEntity(200, responseData, headers=None)
        return response
        
        
# Create embedded server instance.
host = "localhost"
port = 8000
server = EmbeddedServer(host=host,
                        port=port,
                        restClassObjects=[MyRest()])
server.launchServer()