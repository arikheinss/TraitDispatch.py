from typing import TypeVar
import sys
from functools import wraps

typevars = "T W V X Y Z"
for c in typevars.split(" "):
    globals()[c] = TypeVar(c)


def is_more_specific(sig1, sig2):
    "checks if sig1 is more specific than sig2"
    return all(issubclass(a,b) for (a,b) in zip(sig1, sig2))


from dataclasses import dataclass, field

@dataclass
class Node():
    signature: tuple
    methods: object
    children: list = field(default_factory=list)
    caches: set = field(default_factory=set)
    
class Interface():
    def __init__(self, num_params, fnames, name=""):
        self.num_params = num_params
        self.fnames = fnames
        self.methodtable = []
        self.name = name
    def register(self, signature, methods):
        signature = tuple(signature)
        if not len(signature) == self.num_params:
            raise Exception("Wrong amount of params")
        new_node = Node(signature, methods, [])
        inject_node(new_node, self.methodtable)
    def fetch_implementation(self, signature):
        impl = fetch_node(signature, self.methodtable, dict())
        return impl
        
    def __getitem__(self, sigs):
        if not isinstance(sigs, tuple):
            sigs = (sigs, )
        return InterfaceNotation(self, sigs)
    def __str__(self):
        return f"Interface {self.name}: {len(collect_nodes(self.methodtable, set()))} methods"
class InterfaceNotation():
    def __init__(self, interface, sig):
        self.sig = sig
        self.interface = interface

def collect_nodes(lst, s):
    for n in lst:
        s.add(id(n))
        collect_nodes(n.children, s)
    return s

def fetch_node(signature, nodelist, visited):
    candidate = None
    for node in nodelist:

        nid = id(node)
        if nid in visited:
            #don't do the traversal twice
            return visited[nid]
        
        if node.signature == signature:
            # exact matches cannot be topped, just return
            visited[nid] = node
            return node
            
        if is_more_specific(signature, node.signature):            
            
            new_candidate = fetch_node(signature, node.children, visited)
            if new_candidate is None:
                new_candidate = node
            
            # print(f'comparing: {_name}, {new_candidate.signature}')
            #if found is not None and new_candidate is not found:
            #    raise Exception(f"Multiple candidates found for method lookup {signature}: {found.signature} and {new_candidate.signature}")
            if candidate is not None and new_candidate is not candidate:
                raise Exception(f"Multiple candidates found for method lookup {signature}: {candidate.signature} and {new_candidate.signature}")
            candidate = new_candidate
    for node in nodelist:
        visited[id(node)] = candidate
    return candidate
            
# node matches exactly -> return node
# node matches: search node & subtree
#   - case1: result was found earlier => branch terminates
#                                        set already_found mark
#   - case2: new candidate found => other candidate exists? error - register candidate
#                                   already found ? error
# return
#
#
        
def register_cache(node, f, argtypes):
    node.caches.add((f, argtypes))

def clear_cache(node):
    if node is None:
        return
    for f, argtypes in node.caches:
        del f.cache[argtypes]
    node.caches = set()




def inject_node(node, nodelist, parent = None):
    was_injected_here = False
    was_injected = False
    i = 0
    while i < len(nodelist):
        othernode = nodelist[i]
        if othernode is node:
            return
        if node.signature == othernode.signature:
            node.children = othernode.children
            clear_cache(othernode)
            nodelist[i] = node
            return
        elif is_more_specific(othernode.signature, node.signature):
            node.children.append(othernode)
            if not was_injected_here:
                nodelist[i] = node
                clear_cache(parent)
                was_injected = True
                was_injected_here = True
            else:
                del nodelist[i]
                continue
        elif is_more_specific(node.signature, othernode.signature):
            inject_node(node, othernode.children, parent = othernode)
            was_injected = True
        else: pass
        i += 1
    if not was_injected:
        clear_cache(parent)
        nodelist.append(node)


def is_empty_body(f):
    # this is what the compiled bytecode looks like if your function body is just ...
    return f.__code__.co_code == b'\x95\x00g\x00'

def interface(cls): 
    methods = {k:v for (k,v) in cls.__dict__.items() if not (k.startswith("__") and k.endswith("__"))}
    fallbacks = {k:v for (k,v) in methods.items() if not (is_empty_body(v))}
    parameters = cls.__type_params__
    name = cls.__name__
    interface = Interface(len(parameters), methods.keys(), name)

    return interface

class SelfReferential():
    def __init__(self, f):
        self.f = f
def selfrecurse(f):
    return SelfReferential(f)

def implement(*signature):
    def _(cls): 

        methods = {k:v for (k,v) in cls.__dict__.items() if not (k.startswith("__") and k.endswith("__"))}
        name = cls.__name__

        mod = sys.modules.get(cls.__module__)
        if not mod:
            raise RuntimeException("Module of trait not fount")
        trait = mod.__dict__.get(name)
        if not isinstance(trait, Interface):
            raise Exception(f"trait found was not an Interface. (instead: {type(trait)})")

        if not trait.num_params == len(signature):
            raise Exception(f"Wrong number of params. Required {trait.num_params}, but found {signature}")

        for fname in trait.fnames:
            if not fname in cls.__dict__:
                raise Exception(f"Missing implementation: {fname}")

        for (fname, fn) in methods.items():
            if isinstance(fn, SelfReferential):
                # methods[fname] = fn.f
                setattr(cls, fname, fn.f)
            else:
                # methods[fname] = staticmethod(fn)
                setattr(cls, fname, staticmethod(fn))

        trait.register(signature, cls())
        return trait
    return _

DataType = type(int)

def interfaced(f):
    code = f.__code__
    annotations = [f.__annotations__.get(code.co_varnames[i], None) for i in range(code.co_argcount)]
    implementations = []
    for a in annotations:
        if not isinstance(a, InterfaceNotation):
            break
        implementations.append(a)
    arg_annotations  = annotations[len(implementations):]
    f.cache = {}

    def typemerger(idx, args):
        itr = iter(idx)
        i0 = next(itr)
        t = args[i0]
        for i in itr:
            if not args[i] == t:
                raise Exception("Type missmatch in interface: required the Values in positions {idx} to be equivalent")
        return t
            

    def typegetter(t):
        if isinstance(t, DataType):
            return lambda _: t
        occurences = tuple(i for i in range(len(arg_annotations)) if arg_annotations[i] == t)
        if len(occurences) == 1:
            idx = occurences[0]
            return lambda args: args[idx]
        if len(occurences) > 1:
            return lambda args: typemerger(occurences, args)
        raise Exception(f"Type could not be infered")
          
    sig_getters = tuple(tuple(typegetter(t) for t in impl.sig) 
                        for impl in implementations)
    @wraps(f)
    def inner(*args, **kwargs):
        argtypes = tuple(type(arg) for arg in args)
        if (cached := f.cache.get(argtypes)):
            # print("cached: ", argtypes, " - ", f)
            return f(*cached, *args, **kwargs)

        # print("not cached: ", argtypes, " - ", f)
        

        signatures = (tuple(getter(argtypes) for getter in traitsig) 
                      for traitsig in sig_getters)
        nodes = [impl.interface.fetch_implementation(signature) for (signature, impl) in zip(signatures, implementations)]
        for node in nodes:
            register_cache(node, f, argtypes)
        traits = tuple(node.methods for node in nodes)
        f.cache[argtypes] = traits

        return f(*traits, *args, **kwargs)

    return inner




@interface
class Add[T, W, V]():
    def add(x: T, y: W) -> V:...

@implement(list, list, list)
class Add():
    def add(x, y):
        if not len(x) == len(y):
            raise Exception("lenth of lists did not match")
        return [a + b for (a, b) in zip(x,y)]
    
@interface 
class Parse[T, W]():
    def parse(s: T) -> W: ...

@implement(str, int)
class Parse():
    def parse(s):
        return int(s)
    
@implement(str, float)
class Parse():
    def parse(s):
        return 12.5
    
@interfaced
def parseadd(impl: Parse[T, W], x: T, y: W):
    print("implementation:", impl)
    return impl.parse(x) + y 

print(Parse)

parseadd("1", 2)
parseadd("1", 2.3)


@interface
class _Map[T]():
    def map(x: T, f): ...
    def default() -> T: ...

@implement(list)
class _Map():
    def map( lst, f): return [f(x) for x in lst]
    def default(): return []

_MAYBE_NONE = {}
class Maybe():
    def __init__(self, val):
        self.val = val
    def __str__(self):
        return f"Maybe({repr(self.val)})" if not isnone(self) \
                else "MaybeNone"
def MaybeNone(): return Maybe(_MAYBE_NONE)
def isnone(m: Maybe): return m.val is _MAYBE_NONE

@implement(Maybe)
class _Map():
    def map(mb, f): return mb if isnone(mb) \
                        else Maybe(f(mb.val))
    def default(): return MaybeNone()

@interfaced
def map_string(impl: _Map[T], x: T):
    # print(impl)
    return impl.map(x, str)


print(map_string(MaybeNone()))
print(map_string(Maybe(2)))
print(map_string([1,2]))

#@interface
#class Add[T,W,V](): 
#    def add(x: T, y: W) -> V:...

# @implement
# class Add[object, object, object]():
#     def add(x,y):
#         return x+y
