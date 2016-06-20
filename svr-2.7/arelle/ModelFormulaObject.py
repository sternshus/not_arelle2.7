u'''
Created on Dec 9, 2010

@author: Mark V Systems Limited
(c) Copyright 2010 Mark V Systems Limited, All rights reserved.
'''
from collections import defaultdict
import datetime, re
from arelle import XmlUtil, XbrlConst, XPathParser, XPathContext
from arelle.ModelValue import qname, QName
from arelle.ModelObject import ModelObject
from arelle.ModelDtsObject import ModelResource
from arelle.ModelInstanceObject import ModelFact
from arelle.XbrlUtil import typedValue

class Aspect(object):
    LOCATION = 1; LOCATION_RULE = 101
    CONCEPT = 2
    ENTITY_IDENTIFIER = 3; VALUE = 31; SCHEME = 32
    PERIOD = 4; PERIOD_TYPE = 41; START = 42; END = 43; INSTANT = 44; INSTANT_END = 45
    UNIT = 5; UNIT_MEASURES = 51; MULTIPLY_BY = 52; DIVIDE_BY = 53; AUGMENT = 54
    COMPLETE_SEGMENT = 6
    COMPLETE_SCENARIO = 7
    NON_XDT_SEGMENT = 8
    NON_XDT_SCENARIO = 9
    DIMENSIONS = 10  # all dimensions; individual dimensions by their QNames
    OMIT_DIMENSIONS = 11 # dimensions with omit specified
    PRECISION = 95  # not real aspects, just for common processing
    DECIMALS = 96

    label = {
        LOCATION: u"location",
        CONCEPT: u"concept",
        ENTITY_IDENTIFIER: u"entity identifier",  VALUE:u"identifier value", SCHEME: u"scheme",
        PERIOD: u"period", PERIOD_TYPE: u"period type", START: u"period start", END: u"period end", INSTANT: u"period instant",
        UNIT: u"unit", MULTIPLY_BY: u"multiply by", DIVIDE_BY: u"divide by", AUGMENT: u"augment",
        COMPLETE_SEGMENT: u"complete segment",
        COMPLETE_SCENARIO: u"complete scenario",
        NON_XDT_SEGMENT: u"nonXDT segment",
        NON_XDT_SCENARIO: u"nonXDT scenario",
        DIMENSIONS: u"all dimensions",
        OMIT_DIMENSIONS: u"omit dimensions",
        PRECISION: u"precision",
        DECIMALS: u"decimals",
        }

def aspectStr(aspect):
    if aspect in Aspect.label:
        return Aspect.label[aspect]
    else:
        return unicode(aspect)

def isDimensionalAspect(aspect):
    return aspect in (Aspect.DIMENSIONS, Aspect.OMIT_DIMENSIONS) or isinstance(aspect, QName)
    
aspectModelAspect = {   # aspect of the model that corresponds to retrievable aspects
    Aspect.VALUE: Aspect.ENTITY_IDENTIFIER, Aspect.SCHEME:Aspect.ENTITY_IDENTIFIER,
    Aspect.PERIOD_TYPE: Aspect.PERIOD, 
    Aspect.START: Aspect.PERIOD, Aspect.END: Aspect.PERIOD, 
    Aspect.INSTANT: Aspect.PERIOD, Aspect.INSTANT_END: Aspect.PERIOD,
    Aspect.UNIT_MEASURES: Aspect.UNIT, Aspect.MULTIPLY_BY: Aspect.UNIT, Aspect.DIVIDE_BY: Aspect.UNIT
    }

aspectRuleAspects = {   # aspect correspondence to rule-retrievable aspects
    Aspect.ENTITY_IDENTIFIER: (Aspect.VALUE, Aspect.SCHEME),
    Aspect.PERIOD: (Aspect.PERIOD_TYPE, Aspect.START, Aspect.END, Aspect.INSTANT),
    Aspect.UNIT: (Aspect.UNIT_MEASURES, Aspect.MULTIPLY_BY, Aspect.DIVIDE_BY)
    }

aspectModels = {
     u"dimensional": set([  # order by likelyhood of short circuting aspect match tests
             Aspect.CONCEPT, Aspect.PERIOD, Aspect.UNIT, Aspect.LOCATION, Aspect.ENTITY_IDENTIFIER,
             Aspect.DIMENSIONS,
             Aspect.NON_XDT_SEGMENT, Aspect.NON_XDT_SCENARIO]),
     u"non-dimensional": set([
             Aspect.CONCEPT, Aspect.PERIOD, Aspect.UNIT, Aspect.LOCATION, Aspect.ENTITY_IDENTIFIER,
             Aspect.COMPLETE_SEGMENT, Aspect.COMPLETE_SCENARIO]),
     }

aspectFromToken = {
     u"location": Aspect.LOCATION, u"concept": Aspect.CONCEPT, 
     u"entityIdentifier": Aspect.ENTITY_IDENTIFIER, u"entity-identifier": Aspect.ENTITY_IDENTIFIER, 
     u"period": Aspect.PERIOD, u"unit": Aspect.UNIT,
     u"nonXDTSegment": Aspect.NON_XDT_SEGMENT, u"non-XDT-segment": Aspect.NON_XDT_SEGMENT, 
     u"nonXDTScenario": Aspect.NON_XDT_SCENARIO, u"non-XDT-scenario": Aspect.NON_XDT_SCENARIO,
     u"dimension": Aspect.DIMENSIONS, u"dimensions": Aspect.DIMENSIONS,
     u"segment": Aspect.COMPLETE_SEGMENT, u"complete-segment": Aspect.COMPLETE_SEGMENT, 
     u"scenario": Aspect.COMPLETE_SCENARIO, u"complete-scenario": Aspect.COMPLETE_SCENARIO,
     }

aspectToToken = {
     Aspect.LOCATION: u"location", Aspect.CONCEPT: u"concept", 
     Aspect.ENTITY_IDENTIFIER: u"entityIdentifier", Aspect.ENTITY_IDENTIFIER: u"entity-identifier", 
     Aspect.PERIOD: u"period", Aspect.UNIT:u"unit",
     Aspect.NON_XDT_SEGMENT: u"non-XDT-segment", 
     Aspect.NON_XDT_SCENARIO: u"non-XDT-scenario",
     Aspect.DIMENSIONS: u"dimension", Aspect.DIMENSIONS: u"dimensions" ,
     Aspect.COMPLETE_SEGMENT: u"complete-segment", 
     Aspect.COMPLETE_SCENARIO: u"complete-scenario",
     }

aspectElementNameAttrValue = {
        Aspect.LOCATION_RULE: (u"location", XbrlConst.tuple, None, None),
        Aspect.CONCEPT: (u"concept", XbrlConst.formula, None, None),
        Aspect.ENTITY_IDENTIFIER: (u"entityIdentifier", XbrlConst.formula, None, None),
        Aspect.SCHEME: (u"entityIdentifier", XbrlConst.formula, None, None),
        Aspect.VALUE: (u"entityIdentifier", XbrlConst.formula, None, None),
        Aspect.PERIOD: (u"period", XbrlConst.formula, None, None),
        Aspect.PERIOD_TYPE: (u"period", XbrlConst.formula, None, None),
        Aspect.INSTANT: (u"period", XbrlConst.formula, None, None),
        Aspect.START: (u"period", XbrlConst.formula, None, None),
        Aspect.END: (u"period", XbrlConst.formula, None, None),
        Aspect.INSTANT_END: (u"period", XbrlConst.formula, None, None),
        Aspect.UNIT: (u"unit", XbrlConst.formula, None, None),
        Aspect.UNIT_MEASURES: (u"unit", XbrlConst.formula, None, None),
        Aspect.MULTIPLY_BY: (u"multiplyBy", XbrlConst.formula, u"source", u"*"),
        Aspect.DIVIDE_BY: (u"divideBy", XbrlConst.formula, u"source", u"*"),
        Aspect.COMPLETE_SEGMENT: ((u"occFragments", u"occXpath"), XbrlConst.formula, u"occ", u"segment"),
        Aspect.COMPLETE_SCENARIO: ((u"occFragments", u"occXpath"), XbrlConst.formula, u"occ", u"scenario"),
        Aspect.NON_XDT_SEGMENT: ((u"occFragments", u"occXpath"), XbrlConst.formula, u"occ", u"segment"),
        Aspect.NON_XDT_SCENARIO: ((u"occFragments", u"occXpath"), XbrlConst.formula, u"occ", u"scenario"),
        }

class FormulaOptions():
    def __init__(self, savedValues=None):
        self.parameterValues = {} # index is QName, value is typed value
        self.runIDs = None # formula and assertion/assertionset IDs to execute
        self.traceParameterExpressionResult = False
        self.traceParameterInputValue = False
        self.traceCallExpressionSource = False
        self.traceCallExpressionCode = False
        self.traceCallExpressionEvaluation = False
        self.traceCallExpressionResult = False
        self.traceVariableSetExpressionSource = False
        self.traceVariableSetExpressionCode = False
        self.traceVariableSetExpressionEvaluation = False
        self.traceVariableSetExpressionResult = False
        self.timeVariableSetEvaluation = False
        self.traceAssertionResultCounts = False
        self.traceSatisfiedAssertions = False
        self.errorUnsatisfiedAssertions = False
        self.traceUnsatisfiedAssertions = False
        self.traceFormulaRules = False
        self.traceVariablesDependencies = False
        self.traceVariablesOrder = False
        self.traceVariableFilterWinnowing = False
        self.traceVariableFiltersResult = False
        self.traceVariableExpressionSource = False
        self.traceVariableExpressionCode = False
        self.traceVariableExpressionEvaluation = False
        self.traceVariableExpressionResult = False
        if isinstance(savedValues, dict):
            self.__dict__.update(savedValues)
            
    def typedParameters(self):
        return dict((qname(paramName), paramValue)
                    for paramName, paramValue in self.parameterValues.items())
        
        # Note: if adding to this list keep DialogFormulaParameters in sync
    def traceSource(self, traceType):
        if traceType in (Trace.VARIABLE_SET, Trace.FORMULA_RULES): 
            return self.traceVariableSetExpressionSource
        elif traceType == Trace.VARIABLE: 
            return self.traceVariableExpressionSource
        else:
            return False
            
    def traceEvaluation(self, traceType):
        if traceType in (Trace.VARIABLE_SET, Trace.FORMULA_RULES): 
            return self.traceVariableSetExpressionEvaluation
        elif traceType == Trace.VARIABLE: 
            return self.traceVariableExpressionEvaluation
        else:
            return False
               
class Trace():
    PARAMETER = 1
    VARIABLE_SET = 2
    MESSAGE = 3
    FORMULA_RULES = 4
    VARIABLE = 5
    CUSTOM_FUNCTION = 6
    CALL = 7 #such as testcase call or API formula call
    TEST = 8 #such as testcase test or API formula test
    
class ModelFormulaResource(ModelResource):
    def init(self, modelDocument):
        super(ModelFormulaResource, self).init(modelDocument)
        
    @property
    def descendantArcroles(self):
        return ()
    
    def compile(self):
        for arcrole in self.descendantArcroles:
            for modelRel in self.modelXbrl.relationshipSet(arcrole).fromModelObject(self):
                toModelObject = modelRel.toModelObject
                if isinstance(toModelObject,ModelFormulaResource):
                    toModelObject.compile()
                elif toModelObject is not None: # missing to object should be detected as link error
                    self.modelXbrl.error(u"formula:internalError",
                         _(u"Invalid formula object %(element)s"),
                         modelObject=self,
                         element=toModelObject.elementQname)

        
    def variableRefs(self, progs=[], varRefSet=None):
        if varRefSet is None: varRefSet = set()
        if progs:
            XPathParser.variableReferences(progs, varRefSet, self)
        for arcrole in self.descendantArcroles:
            for modelRel in self.modelXbrl.relationshipSet(arcrole).fromModelObject(self):
                toModelObject = modelRel.toModelObject
                if isinstance(toModelObject,ModelFormulaResource):
                    modelRel.toModelObject.variableRefs(varRefSet=varRefSet)
        return varRefSet

    def logLabel(self, preferredRole=u'*', lang=None):
        try:
            return self._logLabel
        except AttributeError:
            self._logLabel = self.genLabel(role=preferredRole,strip=True) or self.id or self.xlinkLabel
            return self._logLabel
    
    
class ModelAssertionSet(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelAssertionSet, self).init(modelDocument)
        self.modelXbrl.hasFormulae = True

    @property
    def descendantArcroles(self):
        return (XbrlConst.assertionSet,)
                
    @property
    def propertyView(self):
        return ((u"id", self.id),
                (u"label", self.xlinkLabel))
        
    def __repr__(self):
        return (u"modelAssertionSet[{0}]{1})".format(self.objectId(),self.propertyView))

class ModelVariableSet(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelVariableSet, self).init(modelDocument)
        self.modelXbrl.modelVariableSets.add(self)
        self.modelXbrl.hasFormulae = True
        
    @property
    def descendantArcroles(self):        
        return (XbrlConst.variableSet, XbrlConst.variableSetFilter, XbrlConst.variableSetPrecondition)
                
    @property
    def aspectModel(self):
        return self.get(u"aspectModel")

    @property
    def implicitFiltering(self):
        return self.get(u"implicitFiltering")

    @property
    def groupFilterRelationships(self):
        try:
            return self._groupFilterRelationships
        except AttributeError:
            self._groupFilterRelationships = self.modelXbrl.relationshipSet(XbrlConst.variableSetFilter).fromModelObject(self)
            return self._groupFilterRelationships
    
    @property
    def xmlElementView(self):        
        return XmlUtil.xmlstring(self, stripXmlns=True, prettyPrint=True)
        
    @property
    def propertyView(self):
        return ((u"id", self.id),
                (u"label", self.xlinkLabel),
                (u"aspectModel", self.aspectModel),
                (u"implicitFiltering", self.implicitFiltering))
        
    def __repr__(self):
        return (u"modelVariableSet[{0}]{1})".format(self.objectId(),self.propertyView))

class ModelFormulaRules(object):
    def init(self, modelDocument):
        super(ModelFormulaRules, self).init(modelDocument)
        
    def clear(self):
        if hasattr(self, u"valueProg"):
            XPathParser.clearProg(self.valueProg)
            self.aspectValues.clear()
            for prog in self.aspectProgs.values():
                XPathParser.clearProg(prog)
            self.aspectValues.clear()
            self.aspectProgs.clear()
            self.typedDimProgAspects.clear()
        super(ModelFormulaRules, self).clear()
    
    def compile(self):
        if not hasattr(self, u"valueProg"):
            self.valueProg = XPathParser.parse(self, self.value, self, u"value", Trace.VARIABLE_SET)
            self.hasPrecision = False
            self.hasDecimals = False
            self.aspectValues = defaultdict(list)
            self.aspectProgs = defaultdict(list)
            self.typedDimProgAspects = set()
            def compileRuleElement(ruleElt, exprs):
                if isinstance(ruleElt,ModelObject):
                    name = ruleElt.localName
                    if name == u"qname":
                        value = qname(ruleElt, XmlUtil.text(ruleElt))
                        if ruleElt.getparent().localName == u"concept":
                            self.aspectValues[Aspect.CONCEPT] = value
                        elif ruleElt.getparent().getparent().get(u"dimension") is not None:
                            self.aspectValues[qname(ruleElt.getparent().getparent(), ruleElt.getparent().getparent().get(u"dimension"))] = value
                    elif name == u"qnameExpression":
                        if ruleElt.getparent().localName == u"concept":
                            exprs = [(Aspect.CONCEPT, XmlUtil.text(ruleElt))]
                        elif ruleElt.getparent().getparent().get(u"dimension") is not None:
                            exprs = [(qname(ruleElt.getparent().getparent(), ruleElt.getparent().getparent().get(u"dimension")), XmlUtil.text(ruleElt))]
                    elif name == u"omit" and ruleElt.getparent().get(u"dimension") is not None:
                        self.aspectValues[Aspect.OMIT_DIMENSIONS].append(qname(ruleElt.getparent(), ruleElt.getparent().get(u"dimension")))
                    elif name == u"value" and ruleElt.getparent().get(u"dimension") is not None:
                        self.aspectValues[qname(ruleElt.getparent(), ruleElt.getparent().get(u"dimension"))] = XmlUtil.child(ruleElt,u'*',u'*')
                    elif name == u"xpath" and ruleElt.getparent().get(u"dimension") is not None:
                        typedDimQname = qname(ruleElt.getparent(), ruleElt.getparent().get(u"dimension"))
                        self.typedDimProgAspects.add(typedDimQname)
                        exprs = [(typedDimQname, XmlUtil.text(ruleElt))]
                    elif name == u"entityIdentifier":
                        if ruleElt.get(u"scheme") is not None:
                            exprs.append((Aspect.SCHEME, ruleElt.get(u"scheme")))
                        if ruleElt.get(u"value") is not None:
                            exprs.append((Aspect.VALUE, ruleElt.get(u"value")))
                    elif name == u"instant":
                        self.aspectValues[Aspect.PERIOD_TYPE] = name
                        if ruleElt.get(u"value") is not None:
                            exprs = [(Aspect.INSTANT, ruleElt.get(u"value"))]
                    elif name == u"duration":
                        self.aspectValues[Aspect.PERIOD_TYPE] = name
                        if ruleElt.get(u"start") is not None:
                            exprs.append((Aspect.START, ruleElt.get(u"start")))
                        if ruleElt.get(u"end") is not None:
                            exprs.append((Aspect.END, ruleElt.get(u"end")))
                    elif name == u"forever":
                        self.aspectValues[Aspect.PERIOD_TYPE] = name
                    elif name == u"unit" and ruleElt.get(u"augment") is not None:
                        self.aspectValues[Aspect.AUGMENT] = ruleElt.get(u"augment")
                    elif name == u"multiplyBy":
                        if ruleElt.get(u"measure") is not None:
                            exprs = [(Aspect.MULTIPLY_BY, ruleElt.get(u"measure"))]
                        if ruleElt.getparent().getparent().get(u"source") is not None:
                            self.aspectValues[Aspect.MULTIPLY_BY].append(qname(ruleElt, ruleElt.get(u"source"), noPrefixIsNoNamespace=True))
                    elif name == u"divideBy":
                        if ruleElt.get(u"measure") is not None:
                            exprs = [(Aspect.DIVIDE_BY, ruleElt.get(u"measure"))]
                        if ruleElt.getparent().getparent().get(u"source") is not None:
                            self.aspectValues[Aspect.DIVIDE_BY].append(qname(ruleElt, ruleElt.get(u"source"), noPrefixIsNoNamespace=True))
                    elif name in (u"occEmpty", u"occFragments", u"occXpath"):
                        if ruleElt.get(u"occ") == u"segment":
                            if self.aspectModel == u"dimensional": aspect = Aspect.NON_XDT_SEGMENT
                            else: aspect = Aspect.COMPLETE_SEGMENT
                        else:
                            if self.aspectModel == u"dimensional": aspect = Aspect.NON_XDT_SCENARIO
                            else: aspect = Aspect.COMPLETE_SCENARIO
                        if name == u"occFragments":
                            for occFragment in XmlUtil.children(ruleElt, None, u"*"):
                                self.aspectValues[aspect].append(occFragment)
                        elif name == u"occXpath":
                            exprs = [(aspect, ruleElt.get(u"select"))]
                        elif name == u"occEmpty":
                            self.aspectValues[aspect].insert(0, XbrlConst.qnFormulaOccEmpty)
                    elif name in (u"explicitDimension", u"typedDimension") and ruleElt.get(u"dimension") is not None:
                        qnDim = qname(ruleElt, ruleElt.get(u"dimension"))
                        self.aspectValues[Aspect.DIMENSIONS].append(qnDim)
                        if not XmlUtil.hasChild(ruleElt, XbrlConst.formula, (u"omit",u"member",u"value",u"xpath")):
                            self.aspectValues[qnDim] = XbrlConst.qnFormulaDimensionSAV
                    elif name == u"precision":
                        exprs = [(Aspect.PRECISION, XmlUtil.text(ruleElt))]
                        self.hasPrecision = True
                    elif name == u"decimals":
                        exprs = [(Aspect.DECIMALS, XmlUtil.text(ruleElt))]
                        self.hasDecimals = True
                        
                    if len(exprs) > 0:
                        for aspectExpr in exprs:
                            aspect, expr = aspectExpr
                            self.aspectProgs[aspect].append(XPathParser.parse(self, expr, ruleElt, ruleElt.localName, Trace.FORMULA_RULES))
                        del exprs[:]
                    
                    if name != u"ruleSet": # don't descend ruleSets (table linkbase)
                        for childElt in ruleElt.iterchildren():
                            compileRuleElement(childElt, exprs)
                            
            exprs = []
            for ruleElt in self.iterchildren():
                compileRuleElement(ruleElt, exprs)
            super(ModelFormulaRules, self).compile()

    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelFormulaRules, self).variableRefs([self.valueProg] + [v for vl in self.aspectProgs.values() for v in vl], varRefSet)

    def evaluate(self, xpCtx):
        return xpCtx.atomize( xpCtx.progHeader, xpCtx.evaluate( self.valueProg ) )

    def evaluateRule(self, xpCtx, aspect):
        if aspect in (Aspect.COMPLETE_SEGMENT, Aspect.COMPLETE_SCENARIO,
                        Aspect.NON_XDT_SEGMENT, Aspect.NON_XDT_SCENARIO):
            if not xpCtx: return None
            values = []
            if aspect in self.aspectValues:
                values.extend(self.aspectValues[aspect])
            values.extend(xpCtx.evaluate(prog) for prog in self.aspectProgs[aspect])
            return xpCtx.flattenSequence(values)
        if aspect in self.aspectValues:
            return (self.aspectValues[aspect])
        if aspect in (Aspect.CONCEPT, Aspect.MULTIPLY_BY, Aspect.DIVIDE_BY) or isinstance(aspect, QName):
            type = u'xs:QName'
        elif aspect == Aspect.ENTITY_IDENTIFIER:
            type = u'xs:string'
        elif aspect == Aspect.START:
            type = u'xs:DATETIME_START'
        elif aspect in (Aspect.INSTANT, Aspect.END, Aspect.INSTANT_END):
            type = u'xs:DATETIME_INSTANT_END'
        elif aspect in (Aspect.DECIMALS, Aspect.PRECISION):
            type = u'xs:float'
        else:
            type = u'xs:string'
        if aspect in (Aspect.MULTIPLY_BY, Aspect.DIVIDE_BY): # return list of results
            if aspect in self.aspectProgs:
                return [xpCtx.evaluateAtomicValue(prog, type) for prog in self.aspectProgs[aspect]]
            return []
        elif xpCtx: # return single result
            if aspect in self.aspectProgs: # defaultDict, for loop would add an empty list even if not there
                for prog in self.aspectProgs[aspect]:
                    if aspect in self.typedDimProgAspects:  # typed dim xpath (only), returns a node
                        return xpCtx.flattenSequence(xpCtx.evaluate(prog, xpCtx.inputXbrlInstance.xmlRootElement))
                    else:  # atomic results
                        return xpCtx.evaluateAtomicValue(prog, type, xpCtx.inputXbrlInstance.xmlRootElement)
        return None
                
    def hasRule(self, aspect):
        return aspect in self.aspectValues or aspect in self.aspectProgs

    @property
    def value(self):
        return self.get(u"value")

    @property
    def expression(self):
        return XPathParser.normalizeExpr(self.get(u"value"))

    def source(self, aspect=None, ruleElement=None, acceptFormulaSource=True):
        if aspect is None and ruleElement is None:
            return qname(self, self.get(u"source"), noPrefixIsNoNamespace=True) if self.get(u"source") else None
        # find nearest source
        if ruleElement is None:
            if aspect == Aspect.DIMENSIONS:  # SAV is the formula element
                return self.source()
            ruleElements = self.aspectRuleElements(aspect)
            if len(ruleElements) > 0: ruleElement = ruleElements[0]
        if ruleElement is None and aspect not in (Aspect.MULTIPLY_BY, Aspect.DIVIDE_BY, Aspect.LOCATION_RULE):
            ruleElement = self
        while (isinstance(ruleElement,ModelObject) and (acceptFormulaSource or ruleElement != self)):
            if ruleElement.get(u"source") is not None:
                return qname(ruleElement, ruleElement.get(u"source"), noPrefixIsNoNamespace=True)
            if ruleElement == self: break
            ruleElement = ruleElement.getparent()
        return None
    
    def aspectRuleElements(self, aspect):
        if aspect in aspectElementNameAttrValue:
            eltName, ns, attrName, attrValue = aspectElementNameAttrValue[aspect]
            return XmlUtil.descendants(self, ns, eltName, attrName, attrValue)
        elif isinstance(aspect,QName):
            return [d 
                    for d in XmlUtil.descendants(self, XbrlConst.formula, (u"explicitDimension", u"typedDimension"))
                    if aspect == qname(d, d.get(u"dimension"))]
        return []
        
class ModelFormula(ModelFormulaRules, ModelVariableSet):
    def init(self, modelDocument):
        super(ModelFormula, self).init(modelDocument)
        
    @property
    def propertyView(self):
        return super(ModelFormula, self).propertyView + (
                 (u"value", self.value),
                 (u"formula", XmlUtil.xmlstring(self, stripXmlns=True, prettyPrint=True)))
        
    def __repr__(self):
        return (u"formula({0}, '{1}')".format(self.id if self.id else self.xlinkLabel, self.value))

    @property
    def viewExpression(self):
        return self.value
                
class ModelTuple(ModelFormula):
    def init(self, modelDocument):
        super(ModelTuple, self).init(modelDocument)

class ModelVariableSetAssertion(ModelVariableSet):
    def init(self, modelDocument):
        super(ModelVariableSetAssertion, self).init(modelDocument)
    
    def clear(self):
        XPathParser.clearNamedProg(self, u"testProg")
        super(ModelVariableSetAssertion, self).clear()
    
    def compile(self):
        if not hasattr(self, u"testProg"):
            self.testProg = XPathParser.parse(self, self.test, self, u"test", Trace.VARIABLE_SET)
            super(ModelVariableSetAssertion, self).compile()

    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelVariableSetAssertion, self).variableRefs(self.testProg, varRefSet)

    @property
    def test(self):
        return self.get(u"test")

    @property
    def expression(self):
        return XPathParser.normalizeExpr(self.get(u"test"))

    def message(self,satisfied,preferredMessage=u'*',lang=None):
        msgsRelationshipSet = self.modelXbrl.relationshipSet(XbrlConst.assertionSatisfiedMessage if satisfied else XbrlConst.assertionUnsatisfiedMessage)
        if msgsRelationshipSet:
            return msgsRelationshipSet.label(self, preferredMessage, lang, returnText=False)
        return None
    
    @property
    def propertyView(self):
        return super(ModelVariableSetAssertion, self).propertyView + ((u"test", self.test),)
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__,self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.get(u"test")
                
class ModelExistenceAssertion(ModelVariableSetAssertion):
    def init(self, modelDocument):
        self.evaluationsCount = 0
        super(ModelExistenceAssertion, self).init(modelDocument)
                
class ModelValueAssertion(ModelVariableSetAssertion):
    def init(self, modelDocument):
        super(ModelValueAssertion, self).init(modelDocument)
                
    def evaluate(self, xpCtx):
        try:
            return xpCtx.evaluate(self.testProg) 
        except AttributeError:
            return None
            
class ModelConsistencyAssertion(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelConsistencyAssertion, self).init(modelDocument)
        self.modelXbrl.hasFormulae = True
                
    def clear(self):
        XPathParser.clearNamedProg(self, u"radiusProg")
        super(ModelConsistencyAssertion, self).clear()
    
    def compile(self):
        if not hasattr(self, u"radiusProg"):
            self.radiusProg = XPathParser.parse(self, self.radiusExpression, self, u"radius", Trace.VARIABLE_SET)
            super(ModelConsistencyAssertion, self).compile()

    def evalRadius(self, xpCtx, factValue):
        try:
            return xpCtx.evaluateAtomicValue(self.radiusProg, u'xs:float', factValue)
        except:
            return None
    @property
    def descendantArcroles(self):
        return (XbrlConst.consistencyAssertionFormula,)
        
    @property
    def hasProportionalAcceptanceRadius(self):
        return self.get(u"proportionalAcceptanceRadius") is not None
        
    @property
    def hasAbsoluteAcceptanceRadius(self):
        return self.get(u"absoluteAcceptanceRadius") is not None

    @property
    def isStrict(self):
        return self.get(u"strict") == u"true"

    def message(self,satisfied,preferredMessage=u'*',lang=None):
        msgsRelationshipSet = self.modelXbrl.relationshipSet(XbrlConst.assertionSatisfiedMessage if satisfied else XbrlConst.assertionUnsatisfiedMessage)
        if msgsRelationshipSet:
            msg = msgsRelationshipSet.label(self, preferredMessage, lang, returnText=False)
            if msg is not None:
                return msg
        return None
    
    @property
    def radiusExpression(self):
        if self.get(u"proportionalAcceptanceRadius") is not None:
            return self.get(u"proportionalAcceptanceRadius")
        elif self.get(u"absoluteAcceptanceRadius") is not None:
            return self.get(u"absoluteAcceptanceRadius")
        return u""

    @property
    def viewExpression(self):
        if self.get(u"proportionalAcceptanceRadius") is not None:
            return u"proportionalAcceptanceRadius=" + self.get(u"proportionalAcceptanceRadius")
        elif self.get(u"absoluteAcceptanceRadius") is not None:
            return u"absoluteAcceptanceRadius=" + self.get(u"absoluteAcceptanceRadius")
        return u""
    
    @property
    def xmlElementView(self):        
        return XmlUtil.xmlstring(self, stripXmlns=True, prettyPrint=True)

    @property
    def propertyView(self):
        return ((u"id", self.id),
                (u"label", self.xlinkLabel),
                (u"proportional radius", self.get(u"proportionalAcceptanceRadius")) if self.get(u"proportionalAcceptanceRadius") else (),
                (u"absolute radius", self.get(u"absoluteAcceptanceRadius")) if self.get(u"absoulteAcceptanceRadius") else () ,
                (u"strict", unicode(self.isStrict).lower()))
        
    def __repr__(self):
        return (u"modelConsistencyAssertion[{0}]{1})".format(self.objectId(),self.propertyView))
                
class ModelParameter(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelParameter, self).init(modelDocument)
        if self.parameterQname in self.modelXbrl.qnameParameters:
            self.modelXbrl.error(u"xbrlve:parameterNameClash",
                _(u"Parameter name used on multiple parameters %(name)s"),
                modelObject=self, name=self.parameterQname)
        else:
            self.modelXbrl.qnameParameters[self.parameterQname] = self
    
    def clear(self):
        XPathParser.clearNamedProg(self, u"selectProg")
        super(ModelParameter, self).clear()
    
    def compile(self):
        if not hasattr(self, u"selectProg"):
            self.selectProg = XPathParser.parse(self, self.select, self, u"select", Trace.PARAMETER)
            super(ModelParameter, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelParameter, self).variableRefs(self.selectProg, varRefSet)
        
    def evaluate(self, xpCtx, typeQname):
        try:
            return xpCtx.evaluateAtomicValue(self.selectProg, typeQname)
        except AttributeError:
            return None
            
    @property
    def name(self):
        return self.get(u"name")
    
    @property
    def parameterQname(self): # cannot overload with element's qname, needed for schema particle validation
        try:
            return self._parameterQname
        except AttributeError:
            self._parameterQname = self.prefixedNameQname(self.name)
            return self._parameterQname
    
    @property
    def select(self):
        return self.get(u"select")
    
    @property
    def required(self):
        return self.get(u"as")
    
    @property
    def asType(self):
        try:
            return self._asType
        except AttributeError:
            self._asType = self.prefixedNameQname(self.get(u"as"))
            return self._asType
    
    @property
    def propertyView(self):
        return ((u"id", self.id),
                (u"label", self.xlinkLabel),
                (u"name", self.name),
                (u"select", self.select) if self.select else () ,
                (u"required", self.required) if self.required else () ,
                (u"as", self.asType) if self.asType else () )
        
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.select

class ModelInstance(ModelParameter):
    def init(self, modelDocument):
        super(ModelInstance, self).init(modelDocument)
        
    @property
    def instanceQname(self):
        return self.parameterQname

class ModelVariable(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelVariable, self).init(modelDocument)
        
    def compile(self):
        super(ModelVariable, self).compile()

    @property
    def bindAsSequence(self):
        return self.get(u"bindAsSequence")

class ModelFactVariable(ModelVariable):
    def init(self, modelDocument):
        super(ModelFactVariable, self).init(modelDocument)
    
    def clear(self):
        XPathParser.clearNamedProg(self, u"fallbackValueProg")
        del self._filterRelationships[:]
        super(ModelFactVariable, self).clear()
    
    def compile(self):
        if not hasattr(self, u"fallbackValueProg"):
            self.fallbackValueProg = XPathParser.parse(self, self.fallbackValue, self, u"fallbackValue", Trace.VARIABLE)
            super(ModelFactVariable, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        try:
            return self._variableRefs
        except AttributeError:
            self._variableRefs = super(ModelFactVariable, self).variableRefs(self.fallbackValueProg, varRefSet)
            return self._variableRefs
        
    @property
    def descendantArcroles(self):        
        return (XbrlConst.variableFilter,)
        
    @property
    def nils(self):
        return self.get(u"nils") if self.get(u"nils") else u"false"
    
    @property
    def matches(self):
        return self.get(u"matches") if self.get(u"matches") else u"false"
    
    @property
    def fallbackValue(self):
        return self.get(u"fallbackValue")
    
    @property
    def filterRelationships(self):
        try:
            return self._filterRelationships
        except AttributeError:
            rels = [] # order so conceptName filter is first (if any) (may want more sorting in future)
            for rel in self.modelXbrl.relationshipSet(XbrlConst.variableFilter).fromModelObject(self):
                if isinstance(rel.toModelObject,ModelConceptName):
                    rels.insert(0, rel)  # put conceptName filters first
                else:
                    rels.append(rel)
            self._filterRelationships = rels
            return rels
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"nils", self.nils),
                (u"matches", self.matches),
                (u"fallbackValue", self.fallbackValue),
                (u"bindAsSequence", self.bindAsSequence) )

    def __repr__(self):
        return (u"modelFactVariable[{0}]{1})".format(self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return (u"fallbackValue =" + self.fallbackValue) if self.fallbackValue else u""

class ModelGeneralVariable(ModelVariable):
    def init(self, modelDocument):
        super(ModelGeneralVariable, self).init(modelDocument)
    
    def clear(self):
        XPathParser.clearNamedProg(self, u"selectProg")
        super(ModelGeneralVariable, self).clear()
    
    def compile(self):
        if not hasattr(self, u"selectProg"):
            self.selectProg = XPathParser.parse(self, self.select, self, u"select", Trace.VARIABLE)
            super(ModelGeneralVariable, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelGeneralVariable, self).variableRefs(self.selectProg, varRefSet)
        
    @property
    def select(self):
        return self.get(u"select")
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"select", self.select) if self.select else () ,
                (u"bindAsSequence", self.bindAsSequence) )
    
    def __repr__(self):
        return (u"modelGeneralVariable[{0}]{1})".format(self.objectId(),self.propertyView))

    @property
    def viewExpression(self):
        return self.select

class ModelPrecondition(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelPrecondition, self).init(modelDocument)
    
    def clear(self):
        XPathParser.clearNamedProg(self, u"testProg")
        super(ModelPrecondition, self).clear()
    
    def compile(self):
        if not hasattr(self, u"testProg"):
            self.testProg = XPathParser.parse(self, self.test, self, u"test", Trace.VARIABLE)
            super(ModelPrecondition, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelPrecondition, self).variableRefs(self.testProg, varRefSet)
        
    @property
    def test(self):
        return self.get(u"test")
    
    def evalTest(self, xpCtx):
        try:
            return xpCtx.evaluateBooleanValue(self.testProg)
        except AttributeError:
            return True # true if no test attribute because predicate has no filtering action
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"test", self.test) )

    def __repr__(self):
        return (u"modelPrecondition[{0}]{1})".format(self.objectId(),self.propertyView))
        
    @property
    def viewExpression(self):
        return self.test

class ModelFilter(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelFilter, self).init(modelDocument)
        
    def aspectsCovered(self, varBinding):
        return set()    #enpty set
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return facts

    def hasNoFilterVariableDependencies(self, xpCtx):
        try:
            return self._hasNoVariableDependencies
        except AttributeError:
            self._hasNoVariableDependencies = len(self.variableRefs() - xpCtx.parameterQnames) == 0
            return self._hasNoVariableDependencies
        
    @property
    def isFilterShared(self):
        try:
            return self._isFilterShared
        except AttributeError:
            self._isFilterShared = len(self.modelXbrl.relationshipSet(u"XBRL-formulae").toModelObject(self)) > 1
            return self._isFilterShared
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),)
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))

class ModelTestFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelTestFilter, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"testProg")
        super(ModelTestFilter, self).clear()
    
    def compile(self):
        if not hasattr(self, u"testProg"):
            self.testProg = XPathParser.parse(self, self.test, self, u"test", Trace.VARIABLE)
            super(ModelTestFilter, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None): # called from subclasses possibly with progs
        return super(ModelTestFilter, self).variableRefs((progs or []) + (self.testProg or []), varRefSet)
        
    @property
    def test(self):
        return self.get(u"test")
    
    def evalTest(self, xpCtx, fact):
        try:
            return xpCtx.evaluateBooleanValue(self.testProg, fact)
        except AttributeError:
            return True # true if no test attribute because predicate has no filtering action
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"test", self.test) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.test

class ModelPatternFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelPatternFilter, self).init(modelDocument)

    @property
    def pattern(self):
        return self.get(u"pattern")
    
    @property
    def rePattern(self):
        try:
            return self._rePattern
        except AttributeError:
            self._rePattern = re.compile(self.pattern)
            return self._rePattern
        
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"pattern", self.pattern) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.pattern

class ModelAspectCover(ModelFilter):
    def init(self, modelDocument):
        super(ModelAspectCover, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProgs(self, u"excludedDimQnameProgs")
        XPathParser.clearNamedProgs(self, u"includedDimQnameProgs")
        super(ModelAspectCover, self).clear()
    
    def aspectsCovered(self, varBinding, xpCtx=None):
        try:
            return self._aspectsCovered
        except AttributeError:
            self._aspectsCovered = set()
            self._dimsExcluded = set()
            self.isAll = False
            self.allDimensions = False
            for aspectElt in XmlUtil.children(self, XbrlConst.acf, u"aspect"):
                aspect = XmlUtil.text(aspectElt)
                if aspect == u"all":
                    self.isAll = True
                    self.allDimensions = True
                    self._aspectsCovered |= set([
                     Aspect.LOCATION, Aspect.CONCEPT, Aspect.ENTITY_IDENTIFIER, Aspect.PERIOD, Aspect.UNIT,
                     Aspect.NON_XDT_SEGMENT, Aspect.NON_XDT_SCENARIO, 
                     Aspect.COMPLETE_SEGMENT, Aspect.COMPLETE_SCENARIO])
                elif aspect == u"dimensions":
                    self.allDimensions = True
                else:
                    self._aspectsCovered.add( aspectFromToken[aspect] )
            for dimElt in XmlUtil.descendants(self, XbrlConst.acf, u"qname"):
                dimAspect = qname( dimElt, XmlUtil.text(dimElt) )
                if dimElt.getparent().localName == u"excludeDimension":
                    self._dimsExcluded.add(dimAspect)
                else:
                    self._aspectsCovered.add(dimAspect)
            if xpCtx:   # provided during validate formula checking
                for dimProgs, isExcluded in ((self.includedDimQnameProgs, False),(self.excludedDimQnameProgs, True)):
                    for dimProg in dimProgs:
                        dimAspect = xpCtx.evaluateAtomicValue(dimProg, u'xs:QName')
                        if isExcluded:
                            self._dimsExcluded.add(dimAspect)
                        else:
                            self._aspectsCovered.add(dimAspect)
            return self._aspectsCovered
        
    def dimAspectsCovered(self, varBinding):
        # if DIMENSIONS are provided then return all varBinding's dimensions less excluded dimensions
        self.aspectsCovered  # must have aspectsCovered initialized before the rest of this method
        dimsCovered = set()
        if self.allDimensions:
            for varBoundAspect in varBinding.aspectsDefined:
                if isinstance(varBoundAspect, QName) and varBoundAspect not in self._dimsExcluded:
                    dimsCovered.add(varBoundAspect)
        return dimsCovered
        
    def compile(self):
        if not hasattr(self, u"includedDimQnameProgs"):
            self.includedDimQnameProgs = []
            self.excludedDimQnameProgs = []
            i = 1
            for qnameExpression in XmlUtil.descendants(self, XbrlConst.acf, u"qnameExpression"):
                qNE = u"qnameExpression_{0}".format(i)
                prog = XPathParser.parse( self, XmlUtil.text(qnameExpression), qnameExpression, qNE, Trace.VARIABLE )
                if qnameExpression.getparent().localName == u"excludeDimension":
                    self.excludedDimQnameProgs.append(prog)
                else:
                    self.includedDimQnameProgs.append(prog)
                i += 1
            super(ModelAspectCover, self).compile()

    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelAspectCover, self).variableRefs(self.includedDimQnameProgs + self.excludedDimQnameProgs, varRefSet)
        
    @property
    def viewExpression(self):
        return XmlUtil.innerTextList(self)

class ModelBooleanFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelBooleanFilter, self).init(modelDocument)
        
    @property
    def descendantArcroles(self):        
        return (XbrlConst.booleanFilter,)

    @property
    def filterRelationships(self):
        return self.modelXbrl.relationshipSet(XbrlConst.booleanFilter).fromModelObject(self)
    
    def aspectsCovered(self, varBinding):
        aspectsCovered = set()
        for rel in self.filterRelationships:
            if rel.isCovered:
                _filter = rel.toModelObject
                if isinstance(_filter, ModelFilter):
                    aspectsCovered |= _filter.aspectsCovered(varBinding)
        return aspectsCovered
        
class ModelAndFilter(ModelBooleanFilter):
    def init(self, modelDocument):
        super(ModelAndFilter, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if self.filterRelationships:
            andedFacts = filterFacts(xpCtx, varBinding, facts, self.filterRelationships, u"and")
        else:
            andedFacts = set()
        return (facts - andedFacts) if cmplmt else andedFacts
        
class ModelOrFilter(ModelBooleanFilter):
    def init(self, modelDocument):
        super(ModelOrFilter, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if self.filterRelationships:
            oredFacts = filterFacts(xpCtx, varBinding, facts, self.filterRelationships, u"or")
        else:
            oredFacts = set()
        return (facts - oredFacts) if cmplmt else oredFacts

class ModelConceptName(ModelFilter):
    def init(self, modelDocument):
        super(ModelConceptName, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProgs(self, u"qnameExpressionProgs")
        super(ModelConceptName, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.CONCEPT])
        
    def compile(self):
        if not hasattr(self, u"qnameExpressionProgs"):
            self.qnameExpressionProgs = []
            i = 1
            for qnameExpression in XmlUtil.descendants(self, XbrlConst.cf, u"qnameExpression"):
                qNE = u"qnameExpression_{0}".format(i)
                self.qnameExpressionProgs.append( XPathParser.parse( self, XmlUtil.text(qnameExpression), qnameExpression, qNE, Trace.VARIABLE ) )
                i += 1
            super(ModelConceptName, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelConceptName, self).variableRefs(self.qnameExpressionProgs, varRefSet)

    @property
    def conceptQnames(self):
        try:
            return self._conceptQnames
        except AttributeError:
            self._conceptQnames = set()
            for qnameElt in XmlUtil.descendants(self, XbrlConst.cf, u"qname"):
                self._conceptQnames.add( qname( qnameElt, XmlUtil.text(qnameElt) ) )
            return self._conceptQnames
    
    @property
    def qnameExpressions(self):
        return [XmlUtil.text(qnameExpression)
                for qnameExpression in XmlUtil.descendants(self, XbrlConst.cf, u"qnameExpression")]
    
    def evalQnames(self, xpCtx, fact):
        try:
            return set(xpCtx.evaluateAtomicValue(exprProg, u'xs:QName', fact) for exprProg in self.qnameExpressionProgs)
        except AttributeError:
            return set()
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if not self.qnameExpressionProgs: # optimize if simple
            qnamedFacts = set.union(*[inst.factsByQname[qn]
                                      for inst in varBinding.instances
                                      for qn in self.conceptQnames])
            return (facts - qnamedFacts) if cmplmt else (facts & qnamedFacts)            
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.qname in self.conceptQnames | self.evalQnames(xpCtx,fact))) 
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"names", self.viewExpression) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return XmlUtil.innerTextList(self)

class ModelConceptPeriodType(ModelFilter):
    def init(self, modelDocument):
        super(ModelConceptPeriodType, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.CONCEPT])
        
    @property
    def periodType(self):
        return self.get(u"periodType")
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        factsOfPeriodType = set.union(*[inst.factsByPeriodType(self.periodType)
                                        for inst in varBinding.instances])
        return (facts - factsOfPeriodType) if cmplmt else (facts & factsOfPeriodType)
        
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"periodType", self.periodType) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.periodType

class ModelConceptBalance(ModelFilter):
    def init(self, modelDocument):
        super(ModelConceptBalance, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.CONCEPT])
        
    @property
    def balance(self):
        return self.get(u"balance")
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ ((fact.concept.balance == self.balance) if fact.concept.balance else (self.balance == u"none"))) 
       
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"balance", self.balance) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.balance

class ModelConceptFilterWithQnameExpression(ModelFilter):
    def init(self, modelDocument):
        super(ModelConceptFilterWithQnameExpression, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProgs(self, u"qnameExpressionProgs")
        super(ModelConceptFilterWithQnameExpression, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.CONCEPT])
        
    @property
    def filterQname(self):
        qnameElt = XmlUtil.descendant(self, XbrlConst.cf, u"qname")
        if qnameElt is not None:
            return qname( qnameElt, XmlUtil.text(qnameElt) )
        return None
    
    @property
    def qnameExpression(self):
        qnExprElt = XmlUtil.descendant(self, XbrlConst.cf, u"qnameExpression")
        return XmlUtil.text(qnExprElt) if qnExprElt is not None else None
    
    def compile(self):
        if not hasattr(self, u"qnameExpressionProg"):
            qnExprElt = XmlUtil.descendant(self, XbrlConst.cf, u"qnameExpression")
            qnExpr = XmlUtil.text(qnExprElt) if qnExprElt is not None else None
            self.qnameExpressionProg = XPathParser.parse(self, qnExpr, qnExprElt, u"qnameExpression", Trace.VARIABLE)
            super(ModelConceptFilterWithQnameExpression, self).compile()

    def variableRefs(self, progs=[], varRefSet=None): # subclass may contribute progs
        return super(ModelConceptFilterWithQnameExpression, self).variableRefs((progs or []) + (self.qnameExpressionProg or []), varRefSet)
        
    def evalQname(self, xpCtx, fact):
        if self.filterQname:
            return self.filterQname
        return xpCtx.evaluateAtomicValue(self.qnameExpressionProg, u'xs:QName', fact)

class ModelConceptCustomAttribute(ModelConceptFilterWithQnameExpression):
    def init(self, modelDocument):
        super(ModelConceptCustomAttribute, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"valueProg")
        super(ModelConceptCustomAttribute, self).clear()
    
    @property
    def value(self):
        return self.get(u"value")

    def compile(self):
        if not hasattr(self, u"valueProg"):
            self.valueProg = XPathParser.parse(self, self.value, self, u"value", Trace.VARIABLE)
            super(ModelConceptCustomAttribute, self).compile()

    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelConceptCustomAttribute, self).variableRefs(self.valueProg, varRefSet)
       
    def evalValue(self, xpCtx, fact):
        if not self.value:
            return None
        try:
            return xpCtx.evaluateAtomicValue(self.valueProg, None, fact)
        except:
            return None
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   for qn in (self.evalQname(xpCtx,fact),)
                   for v in (self.evalValue(xpCtx,fact),)
                   for c in (fact.concept,)
                   if cmplmt ^ (qn is not None and
                                c.get(qn.clarkNotation) is not None and
                                (v is None or v == typedValue(xpCtx.modelXbrl, c, attrQname=qn)))) 

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"value", self.value) if self.value else () ,
                (u"qname", self.filterQname) if self.filterQname else () ,
                (u"qnameExpr", self.qnameExpression) if self.qnameExpression else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return (XmlUtil.innerTextList(self) + 
                (u" = " + self.value) if self.value else u"")

class ModelConceptDataType(ModelConceptFilterWithQnameExpression):
    def init(self, modelDocument):
        super(ModelConceptDataType, self).init(modelDocument)

    @property
    def strict(self):
        return self.get(u"strict")
       
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        notStrict = self.strict != u"true"
        if self.filterQname: # optimize if simple without a formula
            factsOfType = set.union(*[inst.factsByDatatype(notStrict, self.filterQname)
                                      for inst in varBinding.instances])
            return (facts - factsOfType) if cmplmt else (facts & factsOfType)            
        return set(fact for fact in facts 
                   for qn in (self.evalQname(xpCtx,fact),)
                   for c in (fact.concept,)
                   if cmplmt ^ (c.typeQname == qn or (notStrict and c.type.isDerivedFrom(qn))))

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"strict", self.strict),
                (u"type", self.filterQname) if self.filterQname else () ,
                (u"typeExpr", self.qnameExpression) if self.qnameExpression else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return XmlUtil.innerTextList(self) + u" \n(strict={0})".format(self.strict)


class ModelConceptSubstitutionGroup(ModelConceptFilterWithQnameExpression):
    def init(self, modelDocument):
        super(ModelConceptSubstitutionGroup, self).init(modelDocument)

    @property
    def strict(self):
        return self.get(u"strict")
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if self.strict == u"true":
            return set(fact for fact in facts 
                       if cmplmt ^ (fact.concept.substitutionGroupQname == self.evalQname(xpCtx,fact)))
        return set(fact for fact in facts 
                   if cmplmt ^ fact.concept.substitutesForQname(self.evalQname(xpCtx,fact)))
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"strict", self.strict),
                (u"subsGrp", self.filterQname) if self.filterQname else () ,
                (u"subsGrpExpr", self.qnameExpression) if self.qnameExpression else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return XmlUtil.innerTextList(self) + u" \n(strict={0})".format(self.strict)

class ModelConceptRelation(ModelFilter):
    def init(self, modelDocument):
        super(ModelConceptRelation, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"sourceQnameExpressionProg")
        XPathParser.clearNamedProg(self, u"linkroleExpressionProg")
        XPathParser.clearNamedProg(self, u"linknameExpressionProg")
        XPathParser.clearNamedProg(self, u"arcroleExpressionProg")
        XPathParser.clearNamedProg(self, u"arcnameExpressionProg")
        XPathParser.clearNamedProg(self, u"testExpressionProg")
        super(ModelConceptRelation, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.CONCEPT])
        
    @property
    def variable(self):
        variableElt = XmlUtil.child(self, XbrlConst.crf, u"variable")
        if variableElt is not None:
            return qname( variableElt, XmlUtil.text(variableElt), noPrefixIsNoNamespace=True )
        return None
    
    @property
    def sourceQname(self):
        sourceQname = XmlUtil.child(self, XbrlConst.crf, u"qname")
        if sourceQname is not None:
            return qname( sourceQname, XmlUtil.text(sourceQname) )
        return None
    
    @property
    def linkrole(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"linkrole")

    @property
    def linkQname(self):
        linkname = XmlUtil.child(self, XbrlConst.crf, u"linkname")
        if linkname:
            return qname( linkname, XmlUtil.text(linkname) )
        return None

    @property
    def arcrole(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"arcrole")

    @property
    def axis(self):
        a = XmlUtil.childText(self, XbrlConst.crf, u"axis")
        if not a: a = u'child'  # would be an XML error
        return a

    @property
    def generations(self):
        try:
            return _INT( XmlUtil.childText(self, XbrlConst.crf, u"generations") )
        except (TypeError, ValueError):
            if self.axis in (u'sibling', u'child', u'parent'): 
                return 1
            return 0
    
    @property
    def test(self):
        return self.get(u"test")

    @property
    def arcQname(self):
        arcnameElt = XmlUtil.child(self, XbrlConst.crf, u"arcname")
        if arcnameElt is not None:
            return qname( arcnameElt, XmlUtil.text(arcnameElt) )
        return None

    @property
    def sourceQnameExpression(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"qnameExpression")

    @property
    def linkroleExpression(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"linkroleExpression")

    @property
    def linknameExpression(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"linknameExpression")

    @property
    def arcroleExpression(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"arcroleExpression")

    @property
    def arcnameExpression(self):
        return XmlUtil.childText(self, XbrlConst.crf, u"arcnameExpression")

    def compile(self):
        if not hasattr(self, u"sourceQnameExpressionProg"):
            self.sourceQnameExpressionProg = XPathParser.parse(self, self.sourceQnameExpression, self, u"sourceQnameExpressionProg", Trace.VARIABLE)
            self.linkroleExpressionProg = XPathParser.parse(self, self.linkroleExpression, self, u"linkroleQnameExpressionProg", Trace.VARIABLE)
            self.linknameExpressionProg = XPathParser.parse(self, self.linknameExpression, self, u"linknameQnameExpressionProg", Trace.VARIABLE)
            self.arcroleExpressionProg = XPathParser.parse(self, self.arcroleExpression, self, u"arcroleQnameExpressionProg", Trace.VARIABLE)
            self.arcnameExpressionProg = XPathParser.parse(self, self.arcnameExpression, self, u"arcnameQnameExpressionProg", Trace.VARIABLE)
            self.testExpressionProg = XPathParser.parse(self, self.test, self, u"testExpressionProg", Trace.VARIABLE)
            super(ModelConceptRelation, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        if self.variable and self.variable != XbrlConst.qnXfiRoot:
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.variable)
        return super(ModelConceptRelation, self).variableRefs(
                                                [p for p in (self.sourceQnameExpressionProg,
                                                 self.linkroleExpressionProg, self.linknameExpressionProg,
                                                 self.arcroleExpressionProg, self.arcnameExpressionProg)
                                                 if p], varRefSet)

    def evalSourceQname(self, xpCtx, fact):
        try:
            if self.sourceQname:
                return self.sourceQname
            return xpCtx.evaluateAtomicValue(self.sourceQnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def evalLinkrole(self, xpCtx, fact):
        try:
            if self.linkrole:
                return self.linkrole
            return xpCtx.evaluateAtomicValue(self.linkroleExpressionProg, u'xs:anyURI', fact)
        except:
            return None
    
    def evalLinkQname(self, xpCtx, fact):
        try:
            if self.linkQname:
                return self.linkQname
            return xpCtx.evaluateAtomicValue(self.linkQnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def evalArcrole(self, xpCtx, fact):
        try:
            if self.arcrole:
                return self.arcrole
            return xpCtx.evaluateAtomicValue(self.arcroleExpressionProg, u'xs:anyURI', fact)
        except:
            return None
    
    def evalArcQname(self, xpCtx, fact):
        try:
            if self.arcQname:
                return self.arcQname
            return xpCtx.evaluateAtomicValue(self.arcQnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def evalTest(self, xpCtx, fact):
        try:
            return xpCtx.evaluateBooleanValue(self.testExpressionProg, fact)
        except:
            return None
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if self.variable:
            otherFact = xpCtx.inScopeVars.get(self.variable)
            sourceQname = otherFact.qname if otherFact is not None else None
        else:
            sourceQname = self.evalSourceQname(xpCtx, None)
        if not sourceQname:
            return set()
        linkrole = self.evalLinkrole(xpCtx, None)
        linkQname = (self.evalLinkQname(xpCtx, None) or () )
        arcrole = self.evalArcrole(xpCtx, None)
        arcQname = (self.evalArcQname(xpCtx, None) or () )
        hasNoTest = self.test is None
        axis = self.axis
        isFromAxis = axis.startswith(u'parent') or axis.startswith(u'ancestor')
        relationships = concept_relationships(xpCtx, None, (sourceQname,
                                                            linkrole,
                                                            arcrole,
                                                            axis.replace(u'-or-self',u''),
                                                            self.generations,
                                                            linkQname,
                                                            arcQname))
        outFacts = set()
        for fact in facts:
            factOk = False
            factQname = fact.qname
            for modelRel in relationships:
                if (((isFromAxis and modelRel.fromModelObject is not None and factQname == modelRel.fromModelObject.qname) or
                     (not isFromAxis and modelRel.toModelObject is not None and factQname == modelRel.toModelObject.qname)) and
                     (hasNoTest or self.evalTest(xpCtx, modelRel))):
                    factOk = True
                    break
            if (not factOk and
                axis.startswith(u'sibling') and
                factQname != sourceQname and 
                not concept_relationships(xpCtx, None, (sourceQname, linkrole, arcrole, u'parent', 1, linkQname, arcQname)) and
                not concept_relationships(xpCtx, None, (factQname, linkrole, arcrole, u'parent', 1, linkQname, arcQname)) and
                concept_relationships(xpCtx, None, (factQname, linkrole, arcrole, u'child', 1, linkQname, arcQname))):
                factOk = True
            if (not factOk and
                axis.endswith(u'-or-self')):
                if sourceQname == XbrlConst.qnXfiRoot:
                    if (not concept_relationships(xpCtx, None, (factQname, linkrole, arcrole, u'parent', 1, linkQname, arcQname)) and
                        concept_relationships(xpCtx, None, (factQname, linkrole, arcrole, u'child', 1, linkQname, arcQname))):
                        factOk = True
                else:
                    if factQname == sourceQname:
                        factOk = True
            if cmplmt ^ (factOk):
                outFacts.add(fact)
        return outFacts 
    
    @property
    def viewExpression(self):
        return u' \n'.join(u"{}: {}".format(e.localName, e.text) for e in XmlUtil.children(self, u"*", u"*"))
    
    @property
    def xmlElementView(self):        
        return XmlUtil.xmlstring(self, stripXmlns=True, prettyPrint=True)

class ModelEntityIdentifier(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelEntityIdentifier, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and
                                self.evalTest(xpCtx, 
                                              fact.context.entityIdentifierElement)))
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.ENTITY_IDENTIFIER])
        
class ModelEntitySpecificIdentifier(ModelFilter):
    def init(self, modelDocument):
        super(ModelEntitySpecificIdentifier, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"schemeProg")
        XPathParser.clearNamedProg(self, u"valueProg")
        super(ModelEntitySpecificIdentifier, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.ENTITY_IDENTIFIER])
        
    @property
    def scheme(self):
        return self.get(u"scheme")
    
    @property
    def value(self):
        return self.get(u"value")
    
    def compile(self):
        if not hasattr(self, u"schemeProg"):
            self.schemeProg = XPathParser.parse(self, self.scheme, self, u"scheme", Trace.VARIABLE)
            self.valueProg = XPathParser.parse(self, self.value, self, u"value", Trace.VARIABLE)
            super(ModelEntitySpecificIdentifier, self).compile()

    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelEntitySpecificIdentifier, self).variableRefs((self.schemeProg or []) + (self.valueProg or []), varRefSet)
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and ( 
                                                 fact.context.entityIdentifier[0] == xpCtx.evaluateAtomicValue(self.schemeProg, u'xs:string', fact) and 
                                                 fact.context.entityIdentifier[1] == xpCtx.evaluateAtomicValue(self.valueProg, u'xs:string', fact))))

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"scheme", self.scheme),
                (u"value", self.value) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return u"{0} {1}".format(self.scheme, self.value)

class ModelEntityScheme(ModelFilter):
    def init(self, modelDocument):
        super(ModelEntityScheme, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"schemeProg")
        super(ModelEntityScheme, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.ENTITY_IDENTIFIER])
        
    @property
    def scheme(self):
        return self.get(u"scheme")
    
    def compile(self):
        if not hasattr(self, u"schemeProg"):
            self.schemeProg = XPathParser.parse(self, self.scheme, self, u"scheme", Trace.VARIABLE)
            super(ModelEntityScheme, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelEntityScheme, self).variableRefs(self.schemeProg, varRefSet)
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                fact.context.entityIdentifier[0] == xpCtx.evaluateAtomicValue(self.schemeProg, u'xs:string', fact))) 

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"scheme", self.scheme) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.scheme

class ModelEntityRegexpIdentifier(ModelPatternFilter):
    def init(self, modelDocument):
        super(ModelEntityRegexpIdentifier, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.ENTITY_IDENTIFIER])
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                self.rePattern.search(fact.context.entityIdentifierElement.xValue) is not None)) 

class ModelEntityRegexpScheme(ModelPatternFilter):
    def init(self, modelDocument):
        super(ModelEntityRegexpScheme, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.ENTITY_IDENTIFIER])
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                self.rePattern.search(fact.context.entityIdentifier[0]) is not None)) 

class ModelGeneral(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelGeneral, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if self.isFilterShared and self.hasNoFilterVariableDependencies(xpCtx): # cache this filter by fact
            if self in xpCtx.cachedFilterResults:
                qualifyingFacts = xpCtx.cachedFilterResults[self]
            else:
                xpCtx.cachedFilterResults[self] = qualifyingFacts = set(fact 
                                                                        for inst in varBinding.instances 
                                                                        for fact in inst.factsInInstance
                                                                        if self.evalTest(xpCtx, fact))
            return (facts - qualifyingFacts) if cmplmt else (facts & qualifyingFacts)            
        return set(fact for fact in facts 
                   if cmplmt ^ (self.evalTest(xpCtx, fact))) 
    
    
class ModelMatchFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelMatchFilter, self).init(modelDocument)

    @property
    def aspectName(self):
        try:
            return self._aspectName
        except AttributeError:
            self._aspectName = self.localName[5].lower() + self.localName[6:]
            return self._aspectName
            
    @property
    def dimension(self):
        return qname( self, self.get(u"dimension")) if self.get(u"dimension") else None
    
    @property
    def matchAny(self):
        try:
            return self._matchAny
        except AttributeError:
            self._matchAny = self.get(u"matchAny") in (u"true", u"1")
            return self._matchAny
            
    
    @property
    def aspect(self):
        try:
            return self._aspect
        except AttributeError:
            self._aspect = aspectFromToken[self.aspectName]
            if self._aspect == Aspect.DIMENSIONS:
                self._aspect = self.dimension
            return self._aspect
        
    def aspectsCovered(self, varBinding):
        return set([self.aspect])
        
    @property
    def variable(self):
        return qname( self, self.get(u"variable"), noPrefixIsNoNamespace=True ) if self.get(u"variable") else None
    
    def variableRefs(self, progs=[], varRefSet=None):
        if self.variable: 
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.variable)
        return super(ModelMatchFilter, self).variableRefs(None, varRefSet)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        aspect = self.aspect
        matchAll = not self.matchAny
        otherFact = xpCtx.inScopeVars.get(self.variable)
        # check that otherFact is a single fact or otherwise all match for indicated aspect
        if isinstance(otherFact,(tuple,list)):
            firstFact = None
            hasNonFact = False
            for fact in otherFact:
                if not isinstance(fact,ModelFact):
                    hasNonFact = True
                elif firstFact is None:
                    firstFact = fact
                elif matchAll and not aspectMatches(xpCtx, fact, firstFact, aspect):
                    ### error
                    raise XPathContext.XPathException(xpCtx, u'xbrlmfe:inconsistentMatchedVariableSequence', 
                                                      _(u'Matched variable sequence includes fact {0} inconsistent in aspect {1}').format(
                                                      unicode(fact), aspectStr(aspect)))
                    return cmplmt
            if hasNonFact:
                return set()
            if matchAll: # otherFact has the aspect value that the whole sequence has
                otherFact = firstFact
        if not isinstance(otherFact,(ModelFact,tuple,list)):
            return set()
        if matchAll:
            return set(fact for fact in facts 
                       if cmplmt ^ (aspectMatches(xpCtx, fact, otherFact, aspect))) 
        else:  # each otherFact may be different from the other, any one of which makes the match succeed
            return set(fact for fact in facts 
                       if cmplmt ^ (any(aspectMatches(xpCtx, fact, anotherFact, aspect)
                                        for anotherFact in otherFact))) 

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"aspect", self.aspectName),
                (u"dimension", self.dimension) if self.dimension else (),
                (u"matchAny", self.matchAny.lower())
                (u"variable", self.variable),
                 )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.dimension

class ModelPeriod(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelPeriod, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.PERIOD])
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                self.evalTest(xpCtx, fact.context.period))) 
    
class ModelDateTimeFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelDateTimeFilter, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"dateProg")
        XPathParser.clearNamedProg(self, u"timeProg")
        super(ModelDateTimeFilter, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.PERIOD])
        
    @property
    def date(self):
        return self.get(u"date")
    
    @property
    def time(self):
        return self.get(u"time")
    
    def compile(self):
        if not hasattr(self, u"dateProg"):
            self.dateProg = XPathParser.parse(self, self.date, self, u"date", Trace.VARIABLE)
            if self.time and not hasattr(self, u"timeProg"):
                self.timeProg = XPathParser.parse(self, self.time, self, u"time", Trace.VARIABLE)
            super(ModelDateTimeFilter, self).compile()

    def variableRefs(self, progs=[], varRefSet=None): # no subclasses super to this
        return super(ModelDateTimeFilter, self).variableRefs((self.dateProg or []) + (getattr(self, u"timeProg", None) or []), varRefSet)
        
    def evalDatetime(self, xpCtx, fact, addOneDay=False):
        date = xpCtx.evaluateAtomicValue(self.dateProg, u'xs:date', fact)
        if hasattr(self,u"timeProg"):
            time = xpCtx.evaluateAtomicValue(self.timeProg, u'xs:time', fact)
            return date + time
        if addOneDay:
            return date + datetime.timedelta(1)
        return date
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"date", self.date),
                (u"time", self.time) if self.time else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.date + (u" " + self.time) if self.time else u""

    
class ModelPeriodStart(ModelDateTimeFilter):
    def init(self, modelDocument):
        super(ModelPeriodStart, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                fact.context.startDatetime == self.evalDatetime(xpCtx, fact, addOneDay=False))) 

class ModelPeriodEnd(ModelDateTimeFilter):
    def init(self, modelDocument):
        super(ModelPeriodEnd, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and (fact.context.isStartEndPeriod 
                                                 and fact.context.endDatetime == self.evalDatetime(xpCtx, fact, addOneDay=True)))) 

class ModelPeriodInstant(ModelDateTimeFilter):
    def init(self, modelDocument):
        super(ModelPeriodInstant, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                fact.context.instantDatetime == self.evalDatetime(xpCtx, fact, addOneDay=True))) 
    
class ModelForever(ModelFilter):
    def init(self, modelDocument):
        super(ModelForever, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and fact.context.isForeverPeriod)) 

    def aspectsCovered(self, varBinding):
        return set([Aspect.PERIOD])
        
class ModelInstantDuration(ModelFilter):
    def init(self, modelDocument):
        super(ModelInstantDuration, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.PERIOD])
        
    @property
    def variable(self):
        return qname( self, self.get(u"variable"), noPrefixIsNoNamespace=True ) if self.get(u"variable") else None
    
    def variableRefs(self, progs=[], varRefSet=None):
        if self.variable: 
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.variable)
        return super(ModelInstantDuration, self).variableRefs(None, varRefSet)

    @property
    def boundary(self):
        return self.get(u"boundary")
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        otherFact = xpCtx.inScopeVars.get(self.variable)
        if (otherFact is not None and isinstance(otherFact,ModelFact) and otherFact.isItem and 
            otherFact.context is not None and otherFact.context.isStartEndPeriod):
            if self.boundary == u'start':
                otherDatetime = otherFact.context.startDatetime
            else:
                otherDatetime = otherFact.context.endDatetime
            return set(fact for fact in facts 
                       if cmplmt ^ (fact.isItem and (fact.context is not None and
                                                     fact.context.isInstantPeriod and
                                                     fact.context.instantDatetime == otherDatetime))) 
        return facts # couldn't filter

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"variable", self.variable),
                (u"boundary", self.boundary) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return u"${0} ({1})".format(self.variable, self.boundary)

class MemberModel():
    def __init__(self, qname, qnameExprProg, variable, linkrole, arcrole, axis):
        self.qname = qname
        self.qnameExprProg = qnameExprProg
        self.variable = variable
        self.linkrole = linkrole
        self.arcrole = arcrole
        self.axis = axis
        self.isMemberStatic = qname and not qnameExprProg and not variable and not axis
    
class ModelExplicitDimension(ModelFilter):
    def init(self, modelDocument):
        super(ModelExplicitDimension, self).init(modelDocument)

    def clear(self):
        if hasattr(self, u"dimQnameExpressionProg"):
            XPathParser.clearProg(self.dimQnameExpressionProg)
            for memberModel in self.memberProgs:
                XPathParser.clearProg(memberModel.qnameExprProg)
                memberModel.__dict__.clear()  # dereference
        super(ModelExplicitDimension, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([self.dimQname])
        
    @property
    def dimQname(self):
        try:
            return self._dimQname
        except AttributeError:
            dQn = XmlUtil.child(XmlUtil.child(self,XbrlConst.df,u"dimension"), XbrlConst.df, u"qname")
            self._dimQname = qname( dQn, XmlUtil.text(dQn) ) if dQn is not None else None
            return self._dimQname
    
    @property
    def dimQnameExpression(self):
        qnameExpression = XmlUtil.descendant(XmlUtil.child(self,XbrlConst.df,u"dimension"), XbrlConst.df, u"qnameExpression")
        if qnameExpression:
            return XmlUtil.text(qnameExpression)
        return None    

    def compile(self):
        if not hasattr(self, u"dimQnameExpressionProg"):
            self.dimQnameExpressionProg = XPathParser.parse(self, self.dimQnameExpression, self, u"dimQnameExpressionProg", Trace.VARIABLE)
            self.memberProgs = []
            for memberElt in XmlUtil.children(self, XbrlConst.df, u"member"):
                qnameElt = XmlUtil.child(memberElt, XbrlConst.df, u"qname")
                qnameExpr = XmlUtil.child(memberElt, XbrlConst.df, u"qnameExpression")                
                variableElt = XmlUtil.child(memberElt, XbrlConst.df, u"variable")
                linkrole = XmlUtil.child(memberElt, XbrlConst.df, u"linkrole")
                arcrole = XmlUtil.child(memberElt, XbrlConst.df, u"arcrole")
                axis = XmlUtil.child(memberElt, XbrlConst.df, u"axis")
                memberModel = MemberModel(
                    qname( qnameElt, XmlUtil.text(qnameElt) ) if qnameElt is not None else None,
                    XPathParser.parse(self, XmlUtil.text(qnameExpr), memberElt, u"memQnameExpressionProg", Trace.VARIABLE) if qnameExpr is not None else None,
                    qname( variableElt, XmlUtil.text(variableElt), noPrefixIsNoNamespace=True ) if variableElt is not None else None,
                    XmlUtil.text(linkrole) if linkrole is not None else None,
                    XmlUtil.text(arcrole) if arcrole is not None else None,
                    XmlUtil.text(axis) if axis is not None else None)
                self.memberProgs.append(memberModel)
            super(ModelExplicitDimension, self).compile()
            self.isFilterStatic = (self.dimQname and not self.dimQnameExpressionProg and 
                                   all(mp.isMemberStatic for mp in self.memberProgs))
            if self.isFilterStatic:
                self.staticMemberQnames = set(mp.qname for mp in self.memberProgs)
                dimConcept = self.modelXbrl.qnameConcepts.get(self.dimQname)
                if dimConcept is None or not dimConcept.isExplicitDimension:
                    self.modelXbrl.error(u"xfie:invalidExplicitDimensionQName",
                                         _(u"%(dimension)s is not an explicit dimension concept QName."),
                                         modelObject=self, dimension=self.dimQname)
        
    def variableRefs(self, progs=[], varRefSet=None):
        if varRefSet is None: varRefSet = set()
        memberModelMemberProgs = []
        for memberModel in self.memberProgs:
            if memberModel.variable:
                varRefSet.add(memberModel.variable)
            elif memberModel.qnameExprProg:
                memberModelMemberProgs.append(memberModel.qnameExprProg)
        return super(ModelExplicitDimension, self).variableRefs(memberModelMemberProgs, varRefSet)

    def evalDimQname(self, xpCtx, fact):
        try:
            if self.dimQname:
                return self.dimQname
            return xpCtx.evaluateAtomicValue(self.dimQnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        if self.isFilterStatic:
            dimQname = self.dimQname
            memQnames = self.staticMemberQnames
            if memQnames:
                dimedFacts = set.union(*[inst.factsByDimMemQname(dimQname, memQname)
                                         for inst in varBinding.instances
                                         for memQname in memQnames])
            else:
                dimedFacts = set.union(*[inst.factsByDimMemQname(dimQname)
                                         for inst in varBinding.instances])
            return (facts - dimedFacts) if cmplmt else (facts & dimedFacts)            

        else:
            outFacts = set()
            for fact in facts:
                factOk = True
                dimQname = self.evalDimQname(xpCtx, fact)
                dimConcept = xpCtx.modelXbrl.qnameConcepts.get(dimQname)
                if dimConcept is None or not dimConcept.isExplicitDimension:
                    self.modelXbrl.error(u"xfie:invalidExplicitDimensionQName",
                                         _(u"%(dimension)s is not an explicit dimension concept QName."),
                                         modelObject=self, dimension=dimQname)
                    return set()
                if fact.isItem:
                    memQname = fact.context.dimMemberQname(dimQname)
                    if memQname:
                        if len(self.memberProgs) > 0:
                            factOk = False
                            domainMembersExist = False
                            for memberModel in self.memberProgs:
                                matchMemQname = None
                                if memberModel.qname:
                                    matchMemQname = memberModel.qname
                                elif memberModel.variable:
                                    otherFact = xpCtx.inScopeVars.get(memberModel.variable)
                                    # BUG: could be bound to a sequence!!!
                                    if otherFact is not None and isinstance(otherFact,ModelFact) and otherFact.isItem:
                                        matchMemQname = otherFact.context.dimMemberQname(dimQname)
                                elif memberModel.qnameExprProg:
                                    matchMemQname = xpCtx.evaluateAtomicValue(memberModel.qnameExprProg, u'xs:QName', fact)
                                memConcept = xpCtx.modelXbrl.qnameConcepts.get(matchMemQname)
                                if memConcept is None:
                                    #self.modelXbrl.error(_("{0} is not a domain item concept.").format(matchMemQname), 
                                    #                     "err", "xbrldfe:invalidDomainMember")
                                    return set()
                                if (not memberModel.axis or memberModel.axis.endswith(u'-self')) and \
                                    matchMemQname == memQname:
                                        factOk = True
                                        break
                                elif memberModel.axis and memberModel.linkrole and memberModel.arcrole:
                                    relSet = fact.modelXbrl.relationshipSet(memberModel.arcrole, memberModel.linkrole)
                                    if relSet:
                                        u''' removed by Erratum 2011-03-10
                                        # check for ambiguous filter member network
                                        linkQnames = set()
                                        arcQnames = set()
                                        fromRels = relSet.fromModelObject(memConcept)
                                        if fromRels:
                                            from arelle.FunctionXfi import filter_member_network_members
                                            filter_member_network_members(relSet, fromRels, memberModel.axis.startswith("descendant"), set(), linkQnames, arcQnames)
                                            if len(linkQnames) > 1 or len(arcQnames) > 1:
                                                self.modelXbrl.error(_('Network of linkrole {0} and arcrole {1} dimension {2} contains ambiguous links {3} or arcs {4}').format(
                                                                     memberModel.linkrole, memberModel.arcrole, self.dimQname, linkQnames, arcQnames) ,
                                                                     "err", "xbrldfe:ambiguousFilterMemberNetwork")
                                                return []
                                        '''
                                        if relSet.isRelated(matchMemQname, memberModel.axis, memQname):
                                            factOk = True
                                            break
                                        elif not domainMembersExist and relSet.isRelated(matchMemQname, memberModel.axis):
                                            domainMembersExist = True # don't need to throw an error
                                u''' removed by erratum 2011-03-10
                                else: # check dynamic mem qname for validity
                                    from arelle.ValidateXbrlDimensions import checkPriItemDimValueValidity
                                    if not checkPriItemDimValueValidity(self, fact.concept, dimConcept, memConcept):
                                        self.modelXbrl.error(_("{0} is not a valid domain member for dimension {1} of primary item {2}.").format(matchMemQname, dimConcept.qname, fact.qname), 
                                                             "err", "xbrldfe:invalidDomainMember")
                                        return set()
                                '''
                            u'''
                            if not factOk:
                                if not domainMembersExist and memberModel.axis:
                                    self.modelXbrl.error(_("No member found in the network of explicit dimension concept {0}").format(dimQname), 
                                                         "err", "xbrldfe:invalidDomainMember")
                                    return set()
                            '''
                    else: # no member for dimension
                        factOk = False
                else:
                    factOk = True # don't filter facts which are tuples
                if cmplmt ^ (factOk):
                    outFacts.add(fact)
        return outFacts 

    @property
    def propertyView(self):
        members = []
        for memberElt in XmlUtil.children(self, XbrlConst.df, u"member"):
            member = XmlUtil.childText(memberElt, XbrlConst.df, (u"qname",u"qnameExpression",u"variable"))
            linkrole = XmlUtil.childText(memberElt, XbrlConst.df, u"linkrole")
            arcrole = XmlUtil.childText(memberElt, XbrlConst.df, u"arcrole")
            axis = XmlUtil.childText(memberElt, XbrlConst.df, u"axis")
            if linkrole or arcrole or axis:
                members.append((u"member", member,
                                ((u"linkrole", linkrole) if linkrole else (),
                                 (u"arcrole", arcrole) if arcrole else (),
                                 (u"axis", axis) if axis else (), )))
            else:
                members.append((u"member", member))
        return ((u"label", self.xlinkLabel),
                (u"dim", self.dimQname) if self.dimQname else () ,
                (u"dimExpr", self.dimQnameExpression) if self.dimQnameExpression else () ,
                (u"members", u"({0})".format(len(members)), tuple(members)) if members else (),
                )
    
    @property
    def viewExpression(self):
        lines = []
        if self.dimQname:
            lines.append(u"dimension: {}".format(self.dimQname))
        elif self.dimQnameExpression:
            lines.append(u"dimension: {}".format(self.dimQnameExpression))
        else:
            lines.append(_(u"dimension: not available"))
        for memberElt in XmlUtil.children(self, XbrlConst.df, u"member"):
            lines.append(u"member")
            for e in XmlUtil.children(memberElt, XbrlConst.df, u"*"):
                lines.append(u"  {}: {}".format(e.localName, e.text))
        return u" \n".join(lines)

class ModelTypedDimension(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelTypedDimension, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([self.dimQname])
        
    @property
    def dimQname(self):
        dimQname = XmlUtil.descendant(self, XbrlConst.df, u"qname")
        if dimQname is not None:
            return qname( dimQname, XmlUtil.text(dimQname) )
        return None
    
    @property
    def dimQnameExpression(self):
        qnameExpression = XmlUtil.descendant(self, XbrlConst.df, u"qnameExpression")
        if qnameExpression is not None:
            return XmlUtil.text(qnameExpression)
        return None    
   
    def compile(self):
        if not hasattr(self, u"dimQnameExpressionProg"):
            self.dimQnameExpressionProg = XPathParser.parse(self, self.dimQnameExpression, self, u"dimQnameExpressionProg", Trace.VARIABLE)
            super(ModelTypedDimension, self).compile()

    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelTypedDimension, self).variableRefs(self.dimQnameExpression, varRefSet)
        
    def evalDimQname(self, xpCtx, fact):
        try:
            if self.dimQname:
                return self.dimQname
            return xpCtx.evaluateAtomicValue(self.dimQnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        outFacts = set()
        for fact in facts:
            dimQname = self.evalDimQname(xpCtx, fact)
            dim = fact.context.qnameDims.get(dimQname) if fact.isItem else None
            if cmplmt ^ (dim is not None and
                         (not self.test or
                          # typed dimension test item is the <typedMember> element, not its contents, e.g. dim
                          self.evalTest(xpCtx, dim))):
                outFacts.add(fact)
        return outFacts 
    
    @property
    def viewExpression(self):
        return XmlUtil.innerTextList(self)

class ModelRelativeFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelRelativeFilter, self).init(modelDocument)

    @property
    def variable(self):
        return qname(self, self.get(u"variable"), noPrefixIsNoNamespace=True) if self.get(u"variable") else None
    
    def variableRefs(self, progs=[], varRefSet=None):
        if self.variable: 
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.variable)
        return super(ModelRelativeFilter, self).variableRefs(None, varRefSet)

    def aspectsCovered(self, varBinding):
        return varBinding.aspectsDefined

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        aspectsUncovered = (varBinding.aspectsDefined - varBinding.aspectsCovered)
        otherVarBinding = xpCtx.varBindings.get(self.variable)
        hasOtherFactVar = otherVarBinding and otherVarBinding.isFactVar and not otherVarBinding.isFallback
        otherFact = otherVarBinding.yieldedFact if hasOtherFactVar else None
        return set(fact for fact in facts 
                   if cmplmt ^ (hasOtherFactVar and
                                aspectsMatch(xpCtx, otherFact, fact, aspectsUncovered) and
                                (fact.isTuple or
                                 all(aspectMatches(xpCtx, otherFact, fact, dimAspect)
                                     for dimAspect in fact.context.dimAspects(xpCtx.defaultDimensionAspects)
                                     if (not varBinding.hasAspectValueCovered(dimAspect) and
                                         not otherVarBinding.hasAspectValueCovered(dimAspect))))
                            ))
        
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"variable", self.variable) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return u"${0}".format(self.variable)

class ModelSegmentFilter(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelSegmentFilter, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.COMPLETE_SEGMENT])
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                (fact.context.hasSegment and self.evalTest(xpCtx, fact.context.segment))))
    
class ModelScenarioFilter(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelScenarioFilter, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.COMPLETE_SCENARIO])
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and
                                (fact.context.hasScenario and self.evalTest(xpCtx, fact.context.scenario))))
    
class ModelAncestorFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelAncestorFilter, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.LOCATION])
        
    @property
    def ancestorQname(self):
        ancestorQname = XmlUtil.descendant(self, XbrlConst.tf, u"qname")
        if ancestorQname is not None:
            return qname( ancestorQname, XmlUtil.text(ancestorQname) )
        return None
    
    @property
    def qnameExpression(self):
        qnameExpression = XmlUtil.descendant(self, XbrlConst.tf, u"qnameExpression")
        if qnameExpression:
            return XmlUtil.text(qnameExpression)
        return None    
   
    def compile(self):
        if not hasattr(self, u"qnameExpressionProg"):
            self.qnameExpressionProg = XPathParser.parse(self, self.qnameExpression, self, u"qnameExpressionProg", Trace.VARIABLE)
            super(ModelAncestorFilter, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelAncestorFilter, self).variableRefs(self.qnameExpressionProg, varRefSet)

    def evalQname(self, xpCtx, fact):
        ancestorQname = self.ancestorQname
        if ancestorQname:
            return ancestorQname
        try:
            return xpCtx.evaluateAtomicValue(self.qnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts if cmplmt ^ ( self.evalQname(xpCtx,fact) in fact.ancestorQnames ))
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"ancestor", self.ancestorQname) if self.ancestorQname else () ,
                (u"ancestorExpr", self.qnameExpression) if self.qnameExpression else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.ancestorQname if self.ancestorQname else self.qnameExpression

class ModelParentFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelParentFilter, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"qnameExpressionProg")
        super(ModelParentFilter, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.LOCATION])
        
    @property
    def parentQname(self):
        parentQname = XmlUtil.descendant(self, XbrlConst.tf, u"qname")
        if parentQname is not None:
            return qname( parentQname, XmlUtil.text(parentQname) )
        return None
    
    @property
    def qnameExpression(self):
        qnameExpression = XmlUtil.descendant(self, XbrlConst.tf, u"qnameExpression")
        if qnameExpression:
            return XmlUtil.text(qnameExpression)
        return None
    
    def compile(self):
        if not hasattr(self, u"qnameExpressionProg"):
            self.qnameExpressionProg = XPathParser.parse(self, self.qnameExpression, self, u"qnameExpressionProg", Trace.VARIABLE)
            super(ModelParentFilter, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelParentFilter, self).variableRefs(self.qnameExpressionProg, varRefSet)

    def evalQname(self, xpCtx, fact):
        parentQname = self.parentQname
        if parentQname:
            return parentQname
        try:
            return xpCtx.evaluateAtomicValue(self.qnameExpressionProg, u'xs:QName', fact)
        except:
            return None
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts if cmplmt ^ ( self.evalQname(xpCtx,fact) == fact.parentQname ))
    
   
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"parent", self.parentQname) if self.parentQname else () ,
                (u"parentExpr", self.qnameExpression) if self.qnameExpression else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.parentQname if self.parentQname else self.qnameExpression

class ModelLocationFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelLocationFilter, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"locationProg")
        super(ModelLocationFilter, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.LOCATION])
        
    @property
    def location(self):
        return self.get(u"location")
    
    @property
    def variable(self):
        return qname(self, self.get(u"variable"), noPrefixIsNoNamespace=True) if self.get(u"variable") else None
    
    def compile(self):
        if not hasattr(self, u"locationProg"):
            self.locationProg = XPathParser.parse(self, self.location, self, u"locationProg", Trace.VARIABLE)
            super(ModelLocationFilter, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        if self.variable: 
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.variable)
        return super(ModelLocationFilter, self).variableRefs(progs, varRefSet)

    def evalLocation(self, xpCtx, fact):
        try:
            return set(xpCtx.flattenSequence(xpCtx.evaluate(self.locationProg, fact)))
        except:
            return set()
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        varFacts = xpCtx.inScopeVars.get(self.variable,[])
        if isinstance(varFacts,ModelFact):
            candidateElts = set([varFacts])
        elif isinstance(varFacts,(list,tuple)):
            candidateElts = set(f for f in varFacts if isinstance(f,ModelFact)) 
        return set(fact for fact in facts 
                   if cmplmt ^ ( len(candidateElts & self.evalLocation(xpCtx,fact) ) > 0 ))
   
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"location", self.location),
                (u"variable", self.variable) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return u"{0} ${1}".format(self.location, self.variable)

class ModelSiblingFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelSiblingFilter, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.LOCATION])
        
    @property
    def variable(self):
        return qname(self, self.get(u"variable"), noPrefixIsNoNamespace=True) if self.get(u"variable") else None
    
    def variableRefs(self, progs=[], varRefSet=None):
        if self.variable: 
            if varRefSet is None: varRefSet = set()
            varRefSet.add(self.variable)
        return super(ModelSiblingFilter, self).variableRefs(progs, varRefSet)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        otherFact = xpCtx.inScopeVars.get(self.variable)
        while isinstance(otherFact,(list,tuple)) and len(otherFact) > 0:
            otherFact = otherFact[0]  # dereference if in a list
        if isinstance(otherFact,ModelFact):
            otherFactParent = otherFact.parentElement
        else:
            otherFactParent = None
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.parentElement == otherFactParent))

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"variable", self.variable) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return u"${0}".format(self.variable)

class ModelGeneralMeasures(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelGeneralMeasures, self).init(modelDocument)

    def aspectsCovered(self, varBinding):
        return set([Aspect.UNIT])
        
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isItem and 
                                (fact.isNumeric and self.evalTest(xpCtx, fact.unit))))
    
class ModelSingleMeasure(ModelFilter):
    def init(self, modelDocument):
        super(ModelSingleMeasure, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProg(self, u"qnameExpressionProg")
        super(ModelSingleMeasure, self).clear()
    
    def aspectsCovered(self, varBinding):
        return set([Aspect.UNIT])
        
    @property
    def measureQname(self):
        measureQname = XmlUtil.descendant(self, XbrlConst.uf, u"qname")
        if measureQname is not None:
            return qname( measureQname, XmlUtil.text(measureQname) )
        return None
    
    @property
    def qnameExpression(self):
        qnameExpression = XmlUtil.descendant(self, XbrlConst.uf, u"qnameExpression")
        if qnameExpression is not None:
            return XmlUtil.text(qnameExpression)
        return None
    
    def compile(self):
        if not hasattr(self, u"qnameExpressionProg"):
            self.qnameExpressionProg = XPathParser.parse(self, self.qnameExpression, self, u"qnameExpressionProg", Trace.VARIABLE)
            super(ModelSingleMeasure, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelSingleMeasure, self).variableRefs(self.qnameExpressionProg, varRefSet)

    def evalQname(self, xpCtx, fact):
        measureQname = self.measureQname
        if measureQname:
            return measureQname
        try:
            return xpCtx.evaluateAtomicValue(self.qnameExpressionProg, u'xs:QName', fact)
        except Exception, ex:
            print u"filter exception {}".format(ex)
            return None
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ (fact.isNumeric and 
                                fact.unit.isSingleMeasure and
                                (fact.unit.measures[0][0] == self.evalQname(xpCtx,fact))))
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"measure", self.qname) if self.qname else () ,
                (u"measureExpr", self.qnameExpression) if self.qnameExpression else () )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.qname if self.qname else self.qnameExpression

class ModelNilFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelNilFilter, self).init(modelDocument)

    def filter(self, xpCtx, varBinding, facts, cmplmt):
        return set(fact for fact in facts 
                   if cmplmt ^ fact.isNil)
    
class ModelPrecisionFilter(ModelFilter):
    def init(self, modelDocument):
        super(ModelPrecisionFilter, self).init(modelDocument)

    @property
    def minimum(self):
        return self.get(u"minimum")
    
    def filter(self, xpCtx, varBinding, facts, cmplmt):
        minimum = self.minimum
        numMinimum = float(u'INF') if minimum == u'INF' else _INT(minimum)
        return set(fact for fact in facts 
                   if cmplmt ^ (self.minimum != u'INF' and
                                not fact.isNil and
                                fact.isNumeric and not fact.isFraction and
                                inferredPrecision(fact) >= numMinimum)) 

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"minimum", self.minimum) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.minimum

class ModelEqualityDefinition(ModelTestFilter):
    def init(self, modelDocument):
        super(ModelEqualityDefinition, self).init(modelDocument)
        
    def evalTest(self, xpCtx, facta, factb):
        xpCtx.inScopeVars[XbrlConst.qnEqualityTestA] = facta
        xpCtx.inScopeVars[XbrlConst.qnEqualityTestB] = factb
        result = super(ModelEqualityDefinition, self).evalTest(xpCtx, facta.modelXbrl)
        xpCtx.inScopeVars.pop(XbrlConst.qnEqualityTestB)
        xpCtx.inScopeVars.pop(XbrlConst.qnEqualityTestA)
        return result

class ModelMessage(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelMessage, self).init(modelDocument)

    def clear(self):
        XPathParser.clearNamedProgs(self, u"expressionProgs")
        super(ModelMessage, self).clear()
    
    @property
    def separator(self):
        return self.get(u"separator")
    
    def compile(self):
        if not hasattr(self, u"expressionProgs") and hasattr(self, u"expressions"):
            self.expressionProgs = []
            i = 1
            for expression in self.expressions:
                name = u"qnameExpression_{0}".format(i)
                self.expressionProgs.append( XPathParser.parse( self, expression, self, name, Trace.MESSAGE ) )
                i += 1
            super(ModelMessage, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None): # no subclass calls this
        try:
            return super(ModelMessage, self).variableRefs(self.expressionProgs, varRefSet)
        except AttributeError:
            return set()    # no expressions

    def evaluate(self, xpCtx):
        return self.formatString.format([xpCtx.evaluateAtomicValue(p, u'xs:string') for p in self.expressionProgs])

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"separator", self.separator) if self.separator else (),
                (u"text", self.text) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return XmlUtil.text(self)
    
class ModelAssertionSeverity(ModelResource):
    def init(self, modelDocument):
        super(ModelAssertionSeverity, self).init(modelDocument)
        
    @property
    def level(self):
        return self.get(u"level")

    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"level", self.level) )
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return self.level
    


class ModelCustomFunctionSignature(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelCustomFunctionSignature, self).init(modelDocument)
        self.modelXbrl.modelCustomFunctionSignatures[self.functionQname, len(self.inputTypes)] = self
        self.modelXbrl.modelCustomFunctionSignatures[self.functionQname] = None # place holder for parser qname recognition
        self.customFunctionImplementation = None

    @property
    def descendantArcroles(self):
        return (XbrlConst.functionImplementation,)
        
    @property
    def name(self):
        try:
            return self._name
        except AttributeError:
            self._name = self.get(u"name")
            return self._name
    
    @property
    def functionQname(self): # cannot overload qname, needed for element and particle validation
        try:
            return self._functionQname
        except AttributeError:
            self._functionQname = self.prefixedNameQname(self.name)
            return self._functionQname
    
    @property
    def outputType(self):
        try:
            return self._outputType
        except AttributeError:
            self._outputType = self.get(u"output")
            return self._outputType
    
    @property
    def inputTypes(self):
        try:
            return self._inputTypes
        except AttributeError:
            self._inputTypes = [elt.get(u"type")
                                for elt in XmlUtil.children(self, XbrlConst.variable, u"input")]
            return self._inputTypes
    
    @property
    def propertyView(self):
        return ((u"label", self.xlinkLabel),
                (u"name", self.name),
                (u"output type", self.outputType) ) + \
                tuple((_(u"input {0}").format(i+1), type) for i,type in enumerate(self.inputTypes))
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))
    
    @property
    def viewExpression(self):
        return _(u"{0}({1}) as {2}").format(self.name, u", ".join(self.inputTypes), self.outputType)


class ModelCustomFunctionImplementation(ModelFormulaResource):
    def init(self, modelDocument):
        super(ModelCustomFunctionImplementation, self).init(modelDocument)
        self.modelXbrl.modelCustomFunctionImplementations.add(self)

    def clear(self):
        XPathParser.clearNamedProg(self, u"outputProg")
        XPathParser.clearNamedProgs(self, u"stepProgs")
        super(ModelCustomFunctionImplementation, self).clear()
    
    @property
    def inputNames(self):
        try:
            return self._inputNames
        except AttributeError:
            self._inputNames = [qname(elt, elt.get(u"name"))
                                for elt in XmlUtil.children(self, XbrlConst.cfi, u"input")]
            return self._inputNames
    
    @property
    def stepExpressions(self):
        try:
            return self._stepExpressions
        except AttributeError:
            self._stepExpressions = [(qname(elt, elt.get(u"name")), elt.text)
                                     for elt in XmlUtil.children(self, XbrlConst.cfi, u"step")]
            return self._stepExpressions
    
    @property
    def outputExpression(self):
        try:
            return self._outputExpression
        except AttributeError:
            outputElt = XmlUtil.child(self, XbrlConst.cfi, u"output")
            self._outputExpression = XmlUtil.text(outputElt) if outputElt is not None else None
            return self._outputExpression
    
    def compile(self):
        if not hasattr(self, u"outputProg"):
            elt = XmlUtil.child(self, XbrlConst.cfi, u"output")
            self.outputProg = XPathParser.parse( self, XmlUtil.text(elt), elt, u"output", Trace.CUSTOM_FUNCTION )
            self.stepProgs = []
            for elt in XmlUtil.children(self, XbrlConst.cfi, u"step"):
                name = u"qnameExpression_{0}".format(qname(elt, elt.get(u"name")))
                self.stepProgs.append( XPathParser.parse( self, elt.text, elt, name, Trace.CUSTOM_FUNCTION ) )
            super(ModelCustomFunctionImplementation, self).compile()
        
    def variableRefs(self, progs=[], varRefSet=None):
        return super(ModelCustomFunctionImplementation, self).variableRefs((self.outputProg or []) + self.stepProgs, varRefSet)

    @property
    def propertyView(self):
        return (((u"label", self.xlinkLabel),) + \
                tuple((_(u"input {0}").format(i+1), unicode(name)) for i,name in enumerate(self.inputNames)) + \
                tuple((_(u"step {0}").format(unicode(qname)), expr) for qname,expr in enumerate(self.stepExpressions)) + \
                ((u"output", self.outputExpression),))
        
    def __repr__(self):
        return (u"{0}[{1}]{2})".format(self.__class__.__name__, self.objectId(),self.propertyView))

    @property
    def viewExpression(self):
        return u' \n'.join([_(u"step ${0}: \n{1}").format(unicode(qname),expr) for qname,expr in self.stepExpressions] +
                          [_(u"output: \n{0}").format(self.outputExpression)])
    

from arelle.ModelObjectFactory import elementSubstitutionModelClass
elementSubstitutionModelClass.update((
     (XbrlConst.qnAssertionSet, ModelAssertionSet),
     (XbrlConst.qnConsistencyAssertion, ModelConsistencyAssertion),
     (XbrlConst.qnExistenceAssertion, ModelExistenceAssertion),
     (XbrlConst.qnValueAssertion, ModelValueAssertion),
     (XbrlConst.qnFormula, ModelFormula),
     (XbrlConst.qnTuple, ModelTuple),
     (XbrlConst.qnParameter, ModelParameter),
     (XbrlConst.qnInstance, ModelInstance),
     (XbrlConst.qnFactVariable, ModelFactVariable),
     (XbrlConst.qnGeneralVariable, ModelGeneralVariable),
     (XbrlConst.qnPrecondition, ModelPrecondition),
     (XbrlConst.qnAspectCover, ModelAspectCover),
     (XbrlConst.qnAndFilter, ModelAndFilter),
     (XbrlConst.qnOrFilter, ModelOrFilter),
     (XbrlConst.qnConceptName, ModelConceptName),
     (XbrlConst.qnConceptBalance, ModelConceptBalance),
     (XbrlConst.qnConceptPeriodType, ModelConceptPeriodType),
     (XbrlConst.qnConceptCustomAttribute, ModelConceptCustomAttribute),
     (XbrlConst.qnConceptDataType, ModelConceptDataType),
     (XbrlConst.qnConceptSubstitutionGroup, ModelConceptSubstitutionGroup),
     (XbrlConst.qnConceptRelation, ModelConceptRelation),
     (XbrlConst.qnExplicitDimension, ModelExplicitDimension),
     (XbrlConst.qnTypedDimension, ModelTypedDimension),
     (XbrlConst.qnEntityIdentifier, ModelEntityIdentifier),
     (XbrlConst.qnEntitySpecificIdentifier, ModelEntitySpecificIdentifier),
     (XbrlConst.qnEntitySpecificScheme, ModelEntityScheme),
     (XbrlConst.qnEntityRegexpIdentifier, ModelEntityRegexpIdentifier),
     (XbrlConst.qnEntityRegexpScheme, ModelEntityRegexpScheme),
     (XbrlConst.qnGeneral, ModelGeneral),
     (XbrlConst.qnMatchConcept, ModelMatchFilter),
     (XbrlConst.qnMatchDimension, ModelMatchFilter),
     (XbrlConst.qnMatchEntityIdentifier, ModelMatchFilter),
     (XbrlConst.qnMatchLocation, ModelMatchFilter),
     (XbrlConst.qnMatchNonXDTScenario, ModelMatchFilter),
     (XbrlConst.qnMatchNonXDTSegment, ModelMatchFilter),
     (XbrlConst.qnMatchPeriod, ModelMatchFilter),
     (XbrlConst.qnMatchScenario, ModelMatchFilter),
     (XbrlConst.qnMatchSegment, ModelMatchFilter),
     (XbrlConst.qnMatchUnit, ModelMatchFilter),
     (XbrlConst.qnPeriod, ModelPeriod),
     (XbrlConst.qnPeriodStart, ModelPeriodStart),
     (XbrlConst.qnPeriodEnd, ModelPeriodEnd),
     (XbrlConst.qnPeriodInstant, ModelPeriodInstant),
     (XbrlConst.qnForever, ModelForever),
     (XbrlConst.qnInstantDuration, ModelInstantDuration),
     (XbrlConst.qnRelativeFilter, ModelRelativeFilter),
     (XbrlConst.qnSegmentFilter, ModelSegmentFilter),
     (XbrlConst.qnScenarioFilter, ModelScenarioFilter),
     (XbrlConst.qnAncestorFilter, ModelAncestorFilter),
     (XbrlConst.qnLocationFilter, ModelLocationFilter),
     (XbrlConst.qnSiblingFilter, ModelSiblingFilter),
     (XbrlConst.qnParentFilter, ModelParentFilter),
     (XbrlConst.qnSingleMeasure, ModelSingleMeasure),
     (XbrlConst.qnGeneralMeasures, ModelGeneralMeasures),
     (XbrlConst.qnNilFilter, ModelNilFilter),
     (XbrlConst.qnPrecisionFilter, ModelPrecisionFilter),
     (XbrlConst.qnEqualityDefinition, ModelEqualityDefinition),
     (XbrlConst.qnMessage, ModelMessage),
     (XbrlConst.qnCustomFunctionSignature, ModelCustomFunctionSignature),
     (XbrlConst.qnCustomFunctionImplementation, ModelCustomFunctionImplementation),
     (XbrlConst.qnAssertionSeverity, ModelAssertionSeverity),
     ))

# import after other modules resolved to prevent circular references
from arelle.FormulaEvaluator import filterFacts, aspectsMatch, aspectMatches
from arelle.FunctionXfi import concept_relationships
from arelle.ValidateXbrlCalcs import inferredPrecision