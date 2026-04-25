from .operations import PDFOperation

def initialize():
    import wx
    from .gui import Main
    app = wx.App(False)
    frame = Main(parent=None)
    frame.m_treeList.AppendColumn("Operation")
    frame.m_treeList.AppendColumn("Type")
    frame.m_treeList.AppendColumn("Text")
    frame.m_treeList.AppendColumn("Changes")
    font_size = frame.m_treeList.GetFont().GetPixelSize()
    frame.m_treeList.SetColumnWidth(col=0, width=30 * font_size[0])
    return app, frame, frame.m_treeList

def append_to_tree_list(operations, tree_list):
    root = tree_list.GetRootItem()
    for operation in operations:
        if (operation.__class__ == PDFOperation):
            continue # only show operations relevant to text processing
        operation_node = tree_list.AppendItem(root, operation.operator)
        tree_list.SetItemText(operation_node, 3, str(getattr(operation, "scheduled_change", "")))
        for operand in operation.get_relevant_operands():
            operand_node = tree_list.AppendItem(operation_node, str(operand))
            tree_list.SetItemText(operand_node, 1, str(type(operand).__name__))
            tree_list.SetItemText(operand_node, 2, getattr(operand, "plain_text", "").replace(" ","␣").replace("\n","↲")) # might also consider ␊ for visualising line breaks
            tree_list.SetItemText(operand_node, 3, str(getattr(operand, "scheduled_change", "")))
        if (operation.operator in ["Td", "Tj", "TJ"]): # only expand operators relevant to text
            tree_list.Expand(operation_node)
            tree_list.Expand(operand_node)