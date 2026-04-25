from pypdf.generic import TextStringObject, ByteStringObject, NumberObject, FloatObject, NameObject
from .context import Context
from typing import Union
from functools import reduce

class PDFOperation:
    def __init__(self, operands, operator, context:Context):
        self.operands = operands
        self.operator = operator
        self.context = context
    @classmethod
    def from_tuple(cls, operands, operator, context:Context):
        operator = operator.decode('ascii') # PDF operators are indeed ascii encoded
        classname = f"PDFOperation{operator}"
        if (classname in globals()):
            # create object of specific class
            return globals()[classname](operands, context)
        else:
            # create object of passthrough-class
            return cls(operands, operator, None)
    # ~ def __repr__(self):
        # ~ return self.operator
    def get_relevant_operands(self):
        return self.operands
    def write_to_stream(self, stream):
        for op in self.operands:
            op.write_to_stream(stream)
            stream.write(b" ")
        stream.write(self.operator.encode("ascii")) # PDF operators are indeed ascii encoded
        stream.write(b"\n")
class PDFOperationTf(PDFOperation):
    def __init__(self, operands, context:Context):
        super().__init__(operands, "Tf", None)
        context.font_key = operands[0]
        context.font_size = operands[1]
class PDFOperationTd(PDFOperation):
    def __init__(self, operands, context:Context):
        super().__init__(operands, "Td", None)
        self.context = context
        self._infer_plain_text()
    def __str__(self):
        return f"{self.operands} {self.operator}"
    def _infer_plain_text(self):
        tx, ty = self.operands
        if (ty != 0):
            # consider a vertical adjustment starting a new line
            ty.plain_text = "\n"
        elif (tx != 0):
            space_width = self.context.get_font_codec().font.space_width
            #print("Td", space_width, tx)
            if (tx > space_width/5):
                # interpret horizontal adjustment as space. total guess.
                # the dummy sample wants tx > space_width/5, the xelatex sample space_width/15.
                tx.plain_text = " "
        return map
class PDFOperationTJ(PDFOperation):
    def __init__(self, operands:list[list[Union[TextStringObject,ByteStringObject,NumberObject]]], context:Context):
        if (len(operands) != 1):
            raise ValueError(f"PDFOperationTJ expects one non-empty Array of Array")
        super().__init__(operands, "TJ", context.clone_shared_font_codecs())
        self._infer_plain_text()
        object_types = set([operand.__class__ for operand in operands])-set([NumberObject.__class__])
        if (len(object_types) > 1):
            raise NotImplementedError(f"Cannot handle Operations with mixed string object types {str(object_types)}.")
    def __str__(self):
        return f"„{self.get_relevant_operands()}“ {self.operator}"
    def _infer_plain_text(self):
        for operand in self.get_relevant_operands():
            if (isinstance(operand, NumberObject) or isinstance(operand, FloatObject)):
                space_width = self.context.get_font_codec().font.space_width
                #print("TJ", space_width, operand)
                if (-operand >= space_width):
                    # a large horizontal adjustment shall be represented as a space
                    operand.plain_text = " "
                pass
            else:
                operand.plain_text = self.context.get_font_codec().decode(operand)
    def get_relevant_operands(self):
        return self.operands[0]
    def set_operand_text(self, text, index):
        sample = self.operands[0][index] # use the operand which is going to be replaced as a sample
        # it is possible that the operand we are going to replace is a space produced by horizontal adjustment
        if (not isinstance(sample, TextStringObject) and not isinstance(sample, ByteStringObject)):
            # in this case, just select any text operand
            sample = next((op for op in self.operands[0] if isinstance(op, TextStringObject) or isinstance(op, ByteStringObject)))
        codec = self.context.get_font_codec()
        if (codec.space_glyph_available()):
            self.operands[0][index] = codec.encode(text, sample)
        else:
            # emulate spaces by inserting horizontal adjustment
            parts = [codec.encode(part, sample) for part in text.split(" ")]
            parts = reduce(lambda l,e: l+[e, NumberObject(-codec.font.space_width*2)], parts, [])
            parts.pop()
            print(parts)
            self.operands[0][index:index+1] = parts
class PDFOperationTj(PDFOperation):
    def __init__(self, operands:list[Union[TextStringObject,ByteStringObject]], context:Context):
        if (len(operands) != 1):
            raise ValueError(f"PDFOperationTj expects one non-empty Array of TextStringObject")
        super().__init__(operands, "Tj", context.clone_shared_font_codecs())
        self._infer_plain_text()
    def __str__(self):
        return f"„{self.get_relevant_operands()}“ {self.operator}"
    def _infer_plain_text(self):
        self.operands[0].plain_text = self.context.get_font_codec().decode(self.operands[0])
    def get_relevant_operands(self):
        return self.operands
    def set_operand_text(self, text, index):
        sample = self.operands[0] # Tj has only one operand
        self.operands[0] = self.context.get_font_codec().encode(text, sample)
