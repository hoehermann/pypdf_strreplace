# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.grid

###########################################################################
## Class Main
###########################################################################

class Main ( wx.Frame ):

    def __init__( self, parent ):
        wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"PyPDF Content Stream Text Analyzer", pos = wx.DefaultPosition, size = wx.Size( 500,300 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )

        bSizer1 = wx.BoxSizer( wx.VERTICAL )

        self.m_grid = wx.grid.Grid( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0 )

        # Grid
        self.m_grid.CreateGrid( 0, 2 )
        self.m_grid.EnableEditing( False )
        self.m_grid.EnableGridLines( True )
        self.m_grid.EnableDragGridSize( True )
        self.m_grid.SetMargins( 0, 0 )

        # Columns
        self.m_grid.AutoSizeColumns()
        self.m_grid.EnableDragColMove( False )
        self.m_grid.EnableDragColSize( True )
        self.m_grid.SetColLabelValue( 0, u"Operation" )
        self.m_grid.SetColLabelValue( 1, u"Text" )
        self.m_grid.SetColLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

        # Rows
        self.m_grid.EnableDragRowSize( True )
        self.m_grid.SetRowLabelAlignment( wx.ALIGN_CENTER, wx.ALIGN_CENTER )

        # Label Appearance

        # Cell Defaults
        self.m_grid.SetDefaultCellAlignment( wx.ALIGN_LEFT, wx.ALIGN_TOP )
        bSizer1.Add( self.m_grid, 1, wx.ALL|wx.EXPAND, 0 )


        self.SetSizer( bSizer1 )
        self.Layout()

        self.Centre( wx.BOTH )

    def __del__( self ):
        pass


