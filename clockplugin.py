#!/usr/bin/env python3

#############################################################################
#
# OnAirScreen Analog Clock QtDesigner Plugin
# Copyright (c) 2012-2022 Sascha Ludwig, astrastudio.de
# All rights reserved.
#

from PyQt5 import QtGui, QtDesigner

from clockwidget import ClockWidget


class ClockPlugin(QtDesigner.QPyDesignerCustomWidgetPlugin):

    def __init__(self, parent=None):
        QtDesigner.QPyDesignerCustomWidgetPlugin.__init__(self)
        self.initialized = False

    def initialize(self, core):
        if self.initialized:
            return
        self.initialized = True

    def isInitialized(self):
        return self.initialized

    def createWidget(self, parent):
        return ClockWidget(parent)

    def name(self):
        return "ClockWidget"

    # Returns the name of the group in Qt Designer's widget box that this
    # widget belongs to.
    def group(self):
        return "PyQt Widgets"

    # Returns the icon used to represent the custom widget in Qt Designer's
    # widget box.
    def icon(self):
        return QtGui.QIcon(_logo_pixmap)

    # Returns a short description of the custom widget for use in a tool tip.
    def toolTip(self):
        return "Tooltip: OAS Clock"

    # Returns a short description of the custom widget for use in a "What's
    # This?" help message for the widget.
    def whatsThis(self):
        return "What's this: OAS Clock"

    # Returns True if the custom widget acts as a container for other widgets;
    # otherwise returns False. Note that plugins for custom containers also
    # need to provide an implementation of the QDesignerContainerExtension
    # interface if they need to add custom editing support to Qt Designer.
    def isContainer(self):
        return False

    # Returns an XML description of a custom widget instance that describes
    # default values for its properties. Each custom widget created by this
    # plugin will be configured using this description.
    def domXml(self):
        return '<widget class="ClockWidget" name="clockWidget" />\n'

    # Returns the module containing the custom widget class. It may include
    # a module path.
    def includeFile(self):
        return "clockwidget"


# Define the image used for the icon.
_logo_32x32_xpm = [
    "32 32 191 2",
    "   c #000000", ".  c #010101", "X  c #030303", "o  c #040404",
    "O  c #060606", "+  c #070707", "@  c #080808", "#  c #090909",
    "$  c #0A0A0A", "%  c #0C0C0C", "&  c #0D0D0D", "*  c #0F0F0F",
    "=  c #101010", "-  c #111111", ";  c #131313", ":  c #141414",
    ">  c #151515", ",  c #171717", "<  c #191919", "1  c #1A1A1A",
    "2  c #1C1C1C", "3  c #1E1E1E", "4  c #1F1F1F", "5  c #202020",
    "6  c #212121", "7  c #222222", "8  c #232323", "9  c #252525",
    "0  c #262626", "q  c #272727", "w  c #292929", "e  c #2A2A2A",
    "r  c #2B2B2B", "t  c #2C2C2C", "y  c #2D2D2D", "u  c #2E2E2E",
    "i  c #313131", "p  c #333333", "a  c #343434", "s  c #353535",
    "d  c #363636", "f  c #383838", "g  c #393939", "h  c #3A3A3A",
    "j  c #3B3B3B", "k  c #3D3D3D", "l  c #3E3E3E", "z  c #3F3F3F",
    "x  c #414141", "c  c #424242", "v  c #434343", "b  c #444444",
    "n  c #454545", "m  c #474747", "M  c #4B4B4B", "N  c #4C4C4C",
    "B  c #4F4F4F", "V  c #505050", "C  c #515151", "Z  c #525252",
    "A  c #535353", "S  c #565656", "D  c #575757", "F  c #595959",
    "G  c #5B5B5B", "H  c #5C5C5C", "J  c #5D5D5D", "K  c #5E5E5E",
    "L  c #606060", "P  c #616161", "I  c #636363", "U  c #646464",
    "Y  c #656565", "T  c #666666", "R  c #676767", "E  c #696969",
    "W  c #6A6A6A", "Q  c #6C6C6C", "!  c #6D6D6D", "~  c #6E6E6E",
    "^  c #6F6F6F", "/  c #737373", "(  c #747474", ")  c #757575",
    "_  c #767676", "`  c #777777", "'  c #787878", "]  c #797979",
    "[  c #7A7A7A", "{  c #7C7C7C", "}  c #7D7D7D", "|  c #7E7E7E",
    " . c #828282", ".. c #838383", "X. c #868686", "o. c #888888",
    "O. c #898989", "+. c #8A8A8A", "@. c #8E8E8E", "#. c #909090",
    "$. c #919191", "%. c #929292", "&. c #939393", "*. c #949494",
    "=. c #979797", "-. c #989898", ";. c #999999", ":. c #9A9A9A",
    ">. c #9B9B9B", ",. c #9C9C9C", "<. c #9D9D9D", "1. c #9E9E9E",
    "2. c #9F9F9F", "3. c #A2A2A2", "4. c #A4A4A4", "5. c #A5A5A5",
    "6. c #A6A6A6", "7. c #A7A7A7", "8. c #A9A9A9", "9. c #AAAAAA",
    "0. c #ABABAB", "q. c #ACACAC", "w. c #ADADAD", "e. c #AEAEAE",
    "r. c #AFAFAF", "t. c #B0B0B0", "y. c #B4B4B4", "u. c #B5B5B5",
    "i. c #B6B6B6", "p. c #B7B7B7", "a. c #BABABA", "s. c #BBBBBB",
    "d. c #BCBCBC", "f. c #BEBEBE", "g. c #C0C0C0", "h. c #C1C1C1",
    "j. c #C2C2C2", "k. c #C3C3C3", "l. c #C4C4C4", "z. c #C5C5C5",
    "x. c #C6C6C6", "c. c #C7C7C7", "v. c #C8C8C8", "b. c #C9C9C9",
    "n. c #CACACA", "m. c #CBCBCB", "M. c #CCCCCC", "N. c #CDCDCD",
    "B. c #CECECE", "V. c #CFCFCF", "C. c #D1D1D1", "Z. c #D2D2D2",
    "A. c #D3D3D3", "S. c #D4D4D4", "D. c #D5D5D5", "F. c #D6D6D6",
    "G. c #D8D8D8", "H. c #D9D9D9", "J. c #DADADA", "K. c #DBDBDB",
    "L. c #DCDCDC", "P. c #DDDDDD", "I. c #DFDFDF", "U. c #E0E0E0",
    "Y. c #E1E1E1", "T. c #E2E2E2", "R. c #E3E3E3", "E. c #E5E5E5",
    "W. c #E6E6E6", "Q. c #E7E7E7", "!. c #E8E8E8", "~. c #EAEAEA",
    "^. c #EBEBEB", "/. c #ECECEC", "(. c #EEEEEE", "). c #EFEFEF",
    "_. c #F0F0F0", "`. c #F1F1F1", "'. c #F2F2F2", "]. c #F4F4F4",
    "[. c #F5F5F5", "{. c #F6F6F6", "}. c #F7F7F7", "|. c #F8F8F8",
    " X c #F9F9F9", ".X c #FAFAFA", "XX c #FBFBFB", "oX c #FCFCFC",
    "OX c #FDFDFD", "+X c #FEFEFE", "@X c #FFFFFF",
    "@X@X@X@X@X@X@X@X@X@X@XD.:.W b u t j J O.l..X@X@X@X@X@X@X+X@X@X@X",
    "@X@X@X@X@X@X+X@X{.3.x         & ; X   .   q ..Y.@X+X@X@X@X@X@X@X",
    "@X@X@X@X+X@X@Xd.y     a ..f.P.x.1.R.n.=.N o   = $.OX@X@X@X@X@X+X",
    "@X@X@X+X@XOX'     K N.@X+X@X@Xr.A @X@X@X+XP.X.:   m R.@X@X@X@X@X",
    "@X+X@X@X|.F   8 i.{ J.@X@X@X@X0.C @X@X@X@X@XS.o.C   q H.@X@X@X@X",
    "+X@X+X+XF   x !.@X%.r _.@X@X@XT.l.+X+X@X+XT.5 r.@X]   8 Y.+X@X@X",
    "+X@X@X[ . z ).@X+X@X! N.@X@X@X@X+X@X@X@X@X| ] @X+X@X}   f  X+X@X",
    "@X@Xk.  4 ~.@X@X@X+X@X@X@X@X@X@X@X+X@X@X@X[.@X@X@X@X@XD   [ @X@X",
    "@X|.u   s.@X@X@X@X+X@X+X@X@X@X@X@X@X@X@X@X@X@X@X@X@X@X_.3 X C.@X",
    "@X9.  v A.+X@X@X+X@X@X+X@X@X@X@X@X@X@X@X@X+X@X@X@X@X@X]...  I @X",
    "@Xn   y.c B Z.@X@X@XOX@X@X@X+X@X@X@X@X@X+X@X+X@X@X_.X.u #.9 # E.",
    "I.o w @X}.O.,.@X+X+X@X@X+X@X@X@X@X+X@X+X@X+X@X@X@XC.T M.+X_   >.",
    "6.  ' @X@X+X@X@X@X@X@X+X@X@X@X@X@X@X@XOX+X@X@X@X@X@X+X@X@Xz.  S ",
    ")   u.@X@X@X@X+X@X@X@X@X@X@X@X@X@X+X@X@X@X@X@X@X@X+X@X@X@X_.- 9 ",
    "Z   J.@X@X@X@X@X@X@X+X@X@X@X@X@X@X@X+X@X+X@X@X@X+X@X@X@X@X@Xi + ",
    "l O s.2.2.G.@X@X@X@X@X@X@X@X@Xp.o.@X@X@X@X@X@X@X@X@X[.5.1.a.b . ",
    "k @ 3.Y Y g.@X@X@X@X@X@X@X@XH.$   r.@X@X@X+X@X@X@X@X).^ Y #.n . ",
    "M   U.+X@X@X+X@X@X@X@X+X@X Xg * 5 9 ].+X@X@X@X@X@X@X@X+X@X@Xd X ",
    "^   d.@X@X@X@X@X@X@X@X@X+X~   e.v.  ' @X@X@X@X@X@X@X@X@X+X[.> 5 ",
    ">.  X.@X@X@X@X@X@X@X+X@X8.  ! @X@XP . D.@X@X@X@X@X+X@X+X@XB.. N ",
    "F.  f OX@X!.b.@X@X@X@XG.& p }.+X@XE.& b @X@X@X@X@XQ.L.+X@XX.  @.",
    "oXs   K.c.5 +.@X@X@X`.e # P.+X@X@X@X;.. 2.@X@X@X@Xf.9 ` !.r X J.",
    "@X-.  R ` 5.@X@X@X@XU.4 7.@X@X@X@X+X+Xp ; /.@X@X@X@XI./ ]   B @X",
    "@X).2 o V.@X@X+X@X@X@X|.+X+X@X@X@X@X+Xn.  E @X@X@X@X@X@Xi   g.+X",
    "+X@X0.  a .X@X@X@X@X@X@X@X@X@X+X@X@X+X@X(   l.@X@X@X@X)   K @X@X",
    "@X+X@XH   P +X@X@X@X<.H.+X@X@X@X@X@X@X@X(., s  X@X+X3.  6 ^.+X@X",
    "@X@X+X'.g . U XX@X4.1 T.@X+X@X].W.@X@X@X@X8.  *.@X2.  % c.@X@X@X",
    "+X@X@X@X!.d   n A.F m.@X+X@X@Xt.K @X@X@X@X@X~  .{   & d.@X+X@X@X",
    "@X+X@X@X@X(.V   % | ^.@X@X@X+Xw.V @X@X@X@X}.q.r   0 v.@X+X@X@X@X",
    "@X@X+X@X@X@X+X&.& . & L t.T. Xv.+.OX/.j.[ 7     Y /.+X+X@X@X@X@X",
    "@X+X@X+X@X@X@X@XL.] <     X 6 s h q &     O F h.@X@X@X@X+X@X@X@X",
    "@X@X+X@X@X@X+X@X@X@X_.e.Q g , o o * y G -.I.+X@X+X@X@X@X@X@X@X@X"]

_logo_pixmap = QtGui.QPixmap(_logo_32x32_xpm)
