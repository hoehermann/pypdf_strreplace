class Change:
    def __str__(self):
        return self.__class__.__name__
    def apply(self, element=None, index=None, collection=None):
        pass

class Delete(Change):
    def apply(self, element=None, index:int=None, collection:list=None):
        collection.pop(index)

class Cluster(Change):
    def apply(self, element:tuple=None, index:int=None, collection:list=None):
        element = collection.pop(index)
        target_index = next((i for i,e in enumerate(collection) if i >= index and e[1] == element[1]), None)
        if (target_index is not None):
            collection.insert(target_index, element)

class Text(Change):
    def __init__(self, text):
        self.text = text
    def __str__(self):
        return f"Set text to „{self.text}“"
    def apply(self, element=None, index=None, collection=None):
        element.set_operand_text(self.text, index)
    
class Surround(Change):
    def __init__(self, prefix, infix, postfix):
        self.prefix = prefix
        self.infix = infix
        self.postfix = postfix
    def __str__(self):
        return f"Surround with „{self.prefix}“ and „{self.postfix}“."
    def apply(self, element=None, index:int=None, collection:list=None):
        self.infix.apply(element, index, collection)
        collection[index+1:index+1] = [self.postfix]
        collection[index:index] = [self.prefix]