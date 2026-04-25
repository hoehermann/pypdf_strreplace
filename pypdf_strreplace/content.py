from .operations import PDFOperation, PDFOperationTJ
from .changes import *
from typing import List
from pypdf.generic import NumberObject, NameObject
import re
from .context import Context

def extract_text(operations: List[PDFOperation]):
    text = ""
    for operation in operations:
        text += "".join([getattr(operand, "plain_text", "") for operand in operation.get_relevant_operands()])
    return text

def schedule_replacements(operations, matches, args_replace):
    text = ""
    match = None
    matches = matches[:]
    first_operation = None
    first_operand = None
    for operation in operations:
        for operand in operation.get_relevant_operands():
            if (hasattr(operand, "plain_text")):
                previous_length = len(text)
                text += operand.plain_text
                while (matches or match):
                    if (match):
                        if (len(text) >= match.end(0)):
                            # we have enough text to cover the end of the current match
                            postfix = operand.plain_text[match.end(0)-previous_length:].strip("\n") # see prefix
                            postfix = match.re.sub(args_replace, postfix) if args_replace is not None else postfix # see prefix
                            new_text = prefix+match.expand(args_replace)+postfix if args_replace is not None else prefix+match.group(0)+postfix
                            first_operand.scheduled_change = Text(new_text)
                            if (operand != first_operand):
                                # the match spans multiple operands
                                # the first operand receives the replacement text in its entirety (with postfix)
                                # we do not need the current operand anymore. mark current operand for deletion
                                operand.scheduled_change = Delete()
                            # we changed an operand in the operation the match begun in
                            # this might be the current operation or a previous one
                            first_operation.scheduled_change = Change()
                            if (operation != first_operation):
                                # the match spans multiple operations
                                # the first operations receives the replacement text in its entirety (with postfix)
                                # we do not need the current operations anymore. mark current operations for deletion
                                operation.scheduled_change = Delete()
                                if (operation.operator in ["TJ"]):
                                    operand_changes = set([c.__class__.__name__ if c else c for c in [getattr(op, "scheduled_change", None) for op in operation.get_relevant_operands()]])
                                    if (operand_changes-set([Delete.__name__])):
                                        #print(f"But wait: Not all the operation's operands are going to be deleted! The operation must be changed, not deleted.")
                                        operation.scheduled_change = Change()
                            # reset text gathering metadata for next match
                            match = None
                            first_operation = None
                            first_operand = None
                        else:
                            # match exists, but the current text does not reach the end
                            # quit looking here and get more text
                            break
                    if (matches):
                        if (len(text) > matches[0].start(0)):
                            match = matches[0]
                            matches.pop(0)
                            # newlines do not actually occur in the PDF. they have been added by us for visual representation. they must be removed here
                            prefix = operand.plain_text[:match.start(0)-previous_length].strip("\n")
                            # one operand might contain multiple matches. since we are focussing on the current match, we must re-do the search and replace in the prefix
                            prefix = match.re.sub(args_replace, prefix) if args_replace is not None else prefix
                            first_operation = operation
                            first_operand = operand
                        else:
                            # match exists, but the current text does not reach the start
                            # quit looking here and get more text
                            break
            if (operation.operator in ["TJ", "Tj"] and first_operand is not None and not hasattr(operand, "scheduled_change")):
                # delete operands containing replaced text
                operand.scheduled_change = Delete()
        if (first_operation is not None and not hasattr(operation, "scheduled_change")):
            # the match spans multiple operations
            # the current operation (might be Tf or something else entirely) did not contain any text and must be removed to avoid confusion
            operation.scheduled_change = Delete()
        if (isinstance(getattr(operation, "scheduled_change", None), Delete) and operation.operator == "Td"):
            # Td movement operations should not be deleted, but rather grouped together and moved behind the replacement
            operation.scheduled_change = Cluster()

def schedule_deletion(operations):
    """Schedule deletion of all text-related operations.
    
    Useful for redacting a document entirely while maintaining design."""
    for operation in operations:
        if (operation.operator in ["TJ", "Tj", "Td", "Tf"]):
            operation.scheduled_change = Delete()

def replace_text(content, context:Context, args_search, args_replace, args_delete, args_indexes, append_to_tree_list):
    # transform plain operations to high-level objects
    operations = [PDFOperation.from_tuple(operands, operator, context) for operands, operator in content.operations]
    
    # flatten mappings into one plain text string
    text = extract_text(operations)

    matches = []
    if (args_search is None and not args_delete):
        # just print
        print("# These are the lines this tool might be able to handle:")
        print(text)
    if (args_search):
        # search in text
        matcher = re.compile(args_search)
        matches = list(matcher.finditer(text))

    if args_indexes is not None:
        matches = [m for i,m in enumerate(matches) if i in args_indexes]

    if (args_search is not None and args_delete is False):
        # look up which operations contributed to each match and schedule to replace them
        schedule_replacements(operations, matches, args_replace)
        schedule_font_switches(operations, context)
    if (args_delete):
        schedule_deletion(operations)
    
    # visualize content stream structure and scheduled changes
    if (append_to_tree_list):
        append_to_tree_list(operations)

    if (args_replace is not None or args_delete is True):
        # do the replacements, but working backwards – else the indices would no longer match
        # we iterate over the list of high-level operations, but we modify the pypdf low-level operations
        for operation_index, operation in reversed(list(enumerate(operations))):
            operation_change = getattr(operation, "scheduled_change", None)
            if (operation_change):
                operation_change.apply(index=operation_index, collection=content.operations)
                if (isinstance(operation_change, Delete)):
                    #print(f"Deleted: {operation}")
                    pass
                elif (isinstance(operation_change, Cluster)):
                    #print(f"Moving together: {operation}")
                    pass
                else:
                    #print(f"Before replacements: {operation}")
                    for operand_index, operand in reversed(list(enumerate(operation.get_relevant_operands()))):
                        operand_change = getattr(operand, "scheduled_change", None)
                        if (operand_change):
                            operand_change.apply(operation, operand_index, operation.get_relevant_operands())
                    #print(f"After replacements:  {operation}")
    #print(content.operations)
    return len(matches) # return amount of matches – which is hopefully the amount of replacements (mind the postfixes!)

def schedule_font_switches(operations, context:Context):
    for operation in operations:
        operation_change = getattr(operation, "scheduled_change", None)
        if (operation_change):
            for operand in operation.get_relevant_operands():
                operand_change = getattr(operand, "scheduled_change", None)
                if (operand_change and isinstance(operand_change, Text)):
                    font_codec = operation.context.get_font_codec()
                    missing_glyphs = font_codec.check_glyph_availability(operand_change.text)
                    if (missing_glyphs):
                        print(missing_glyphs)
                        font_name = font_codec.font.name.split('+')[-1]
                        font_tuple = operation.context.inject_truetype(font_name)
                        operation.scheduled_change = Surround(
                            (font_tuple, b'Tf'),
                            operation_change,
                            ((operation.context.font_key, operation.context.font_size), b'Tf')
                        )
            if (isinstance(operation.scheduled_change, Surround)):
                for operand in operation.get_relevant_operands():
                    if (hasattr(operand, "plain_text") and not hasattr(operand, "scheduled_change")):
                        operand.scheduled_change = Text(operand.plain_text)
                operation.context.font_key = font_tuple[0]
