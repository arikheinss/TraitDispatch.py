from copy import copy

def restrict_dict(d, keys):
    return {k:v for (k,v) in d.items() if k in keys}

class Trait():
    def __init__(self,names, extends = (), fallbacks = {}):
        all_names = set(names)
        fallbacks = copy(fallbacks)
        # TODO
        # If we track not just the names but also the origin of all methods
        # (like in a {name: originaltrait} dict) we can allow diamond-shaped 
        # inheritance, which right now does not work due to clashing names
        for trait in extends:
            if not all_names.isdisjoint(trait.functions):
                raise Exception("Parent traits not disjoint")
            all_names.update(trait.functions)
            fallbacks.update(trait.fallbacks)
            
        self.functions = tuple(all_names)
        self.fallbacks = fallbacks
        self.implementations = {}
        self.parent_methods = merge_methods(extends)
        self.parents = extends
    def register_implementation(self, _type, implementations):
        implementations = restrict_dict(implementations, self.functions)
        for f in self.functions:
            if (not f in implementations):  # and (not f in self.fallbacks):
                parent = self.parent_methods.get(f)
                if (not parent is None) and (_type in parent.implementations):
                    implementations.update(parent.implementations[_type])
                    continue
                if not f in self.fallbacks:
                    raise Exception(f"Missing implementation for {f} in traitdef {self}, {_type}")
        self.implementations[_type] = implementations
        
        for parent in self.parents:
            if not _type in parent.implementations:
                parent.register_implementation(_type, implementations)
                                             
    def get_implementation(self, _type, method):
        return self.implementations[_type].get(method)

def merge_methods(traits):
    methodlist = {}
    for trait in traits:
        for method in trait.functions:
            if (othertrait := methodlist.get(method)):
                raise Exception(f"two traits register the same method {method}: {trait}, {othertrait}")
            methodlist[method] = trait
    return methodlist

class Implements():
    def __init__(self, *traits):
        self.traits = tuple(traits)

    
class TraitImplement():
    def __init__(self, val, traits):
        methodlist = merge_methods(traits)
                
        def prepend_val(f):
            "same as f, but with val prepended to the arglist"
            def _(*args, **kwargs):
                return f(val, *args, **kwargs)
            return _
        
        def prepend_self(f):
            "same as f, but with val prepended to the arglist"
            def _(*args, **kwargs):
                return f(self, *args, **kwargs)
            return _
        
        for (method, trait) in methodlist.items():
            implementation = trait.get_implementation(type(val), method)
            if implementation == None:
                implementation = trait.fallbacks.get(method)
                if implementation is None:
                    raise Exception("no implementation found")
                setattr(self, method, prepend_self(implementation))
            else:
                setattr(self, method, prepend_val(implementation))
            
def withtraits(f):
    annotations = copy(f.__annotations__)
    varnames = f.__code__.co_varnames
    
    trait_annotations = []
    i = 0
    while len(annotations) > 0:
        currentvar = varnames[i]
        if (I := annotations.get(currentvar)):
            del annotations[currentvar]
            if isinstance(I, Implements):
                trait_annotations.append((i, I))
        i += 1
    trait_annotations = tuple(trait_annotations)
    
    def fetch_traits(*args, **kwargs):
        arg_index, arg_traits = trait_annotations[0]
        trait_index = 0
        new_args = []
        for (i, arg) in enumerate(args):
            if i == arg_index:
                new_arg = arg if isinstance(arg, TraitImplement) else TraitImplement(arg, arg_traits.traits)
                new_args.append(new_arg)
                
                trait_index += 1
                if trait_index < len(trait_annotations):
                    arg_index, arg_traits = trait_annotations[trait_index]
            else:
                new_args.append(arg)
        return f(*new_args, **kwargs)
            
            
            
    return fetch_traits

