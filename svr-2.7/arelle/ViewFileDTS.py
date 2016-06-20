u'''
Created on Oct 5, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
import os
from arelle import ViewFile

def viewDTS(modelXbrl, outfile):
    view = ViewDTS(modelXbrl, outfile)
    modelXbrl.modelManager.showStatus(_(u"viewing DTS"))
    view.treeDepth(modelXbrl.modelDocument, 1, set()) # count of cols starts at 1 because no ELR headers as with relationships
    view.addRow([u"DTS"], asHeader=True)
    view.viewDtsElement(modelXbrl.modelDocument, u"entry", 0, set())
    view.close()
    
class ViewDTS(ViewFile.View):
    def __init__(self, modelXbrl, outfile):
        super(ViewDTS, self).__init__(modelXbrl, outfile, u"DTS")
                
    def treeDepth(self, modelDocument, indent, visited):
        visited.add(modelDocument)
        if indent > self.treeCols: self.treeCols = indent
        for referencedDocument in modelDocument.referencesDocument.keys():
            if referencedDocument not in visited:
                self.treeDepth(referencedDocument, indent + 1, visited)
        visited.remove(modelDocument)

    def viewDtsElement(self, modelDocument, referenceType, indent, visited):
        visited.add(modelDocument)
        dtsObjectType = modelDocument.gettype()
        attr = {u"file": modelDocument.basename, u"referenceType": referenceType}
        if not modelDocument.inDTS:
            attr[u"inDTS"] = u"false"
        self.addRow([u"{0} - {1}".format(modelDocument.basename, dtsObjectType)], treeIndent=indent,
                    xmlRowElementName=dtsObjectType, xmlRowEltAttr=attr, xmlCol0skipElt=True)
        for referencedDocument, ref in modelDocument.referencesDocument.items():
            if referencedDocument not in visited:
                self.viewDtsElement(referencedDocument, ref.referenceType, indent + 1, visited)
        visited.remove(modelDocument)
                
