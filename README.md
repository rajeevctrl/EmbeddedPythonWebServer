# EmbeddedPythonWebServer

This module creates a web server from with in the application. There is no need to deploy python script with apache.
Just include this module and your are ready to expose REST endpoints from with on your application

## Usage

Lets assume that you want to expose below python class as rest endpoints:

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

As you can see that we wanted to expose `method1()` of `MyRest` class as rest endpoint. To do so we simply need to decorate the
method with `@RequestMapping(path,produces)` decorator. Where `path` parameter is the relative path to the method and `produces`
denotes the output format of response data. If your have more classes having methods with endpoints
e.g. `MyRest1, MyRest2` then just include those classes as well in the list of classes passed to EmbeddedServer object i.e.

    server = EmbeddedServer(host=host,
                                port=port,
                                restClassObjects=[MyRest(), MyRest1(), MyRest2()])

#### Note

One thing to note is the signature of the method(s) acting as REST endpoints. Each such method should be decorated with
`@RequestMapping()` and return type of each method should be `ResponseEntity()`.
