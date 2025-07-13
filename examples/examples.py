
## Dumb, pointless, syntactic example
def f_g(x,y):
    print("fg: ")
    x.f(y)
    x.g()
  
T = Trait(("f", "g", "fg"), fallbacks = {"fg" : f_g})
W = Trait(("h", "m"))

def noop(*args, **kwargs):
    pass

T.register_implementation(int, {"f" : lambda i,j : print("T.f: int ", i, " extra: ", j),
                                "g" : lambda i: print("T.g: int ", i),})

T.register_implementation(str, {"f" : lambda i: print("T.f: str ", i),
                                "g" : lambda i: print("T.g: str ", i),})

W.register_implementation(str, {"h" : noop, "m" : noop})


@withtraits
def test(a : Implements(T), b, c: Implements(T, W), z: str):
    #print((a.methodlist, a.val))
    #print((c.methodlist, c.val))
    a.f(5)
    a.g()
    c.f()
    c.g()
    a.fg(11)


test(1, 2, "asf", "")


## --------------------------------------------
# Array trait example

CoreArray = Trait(( "get", "length"))
MutArray = Trait(("set",), extends = (CoreArray,))

CoreArray.register_implementation(tuple, {"get" : lambda t, i: t[i], 
                                          "length" : lambda t: len(t)})

def setindex(l, i, v):
    l[i] = v
    return l
MutArray.register_implementation(list, {"get" : lambda t, i: t[i], 
                                        "length" : lambda t: len(t),
                                        "set": setindex})

ResizableArray = Trait(("append",), extends = (MutArray,))

#The missing methods here are looked up from Parent Trait MutArray
ResizableArray.register_implementation(list, {"append" : lambda l,v: l.append(v)})

@withtraits
def print_all(itr: Implements(CoreArray)):
    for i in range(itr.length()):
        print(itr.get(i))
        
print_all((2,3,4,5))

# This works, because the implementation for MutArray for list implies an implementation for CoreArray
print_all([5,6,7])
