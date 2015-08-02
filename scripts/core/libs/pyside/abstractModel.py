import sys
import abc
from PySide import QtGui, QtCore
from core.lib.types import asList, isType, OrderedDict
from core.lib.PySide.functions import addWidget


class InternalMoveWrapper():
    '''
    This wrapper is used to perform internal moves within objects without
    entering infinite loops

    :param object item: the object to control
    :param str method: the method name to enable/disable
    '''
    def __init__(self, item, method='_internalMove'):
        self.__item = item
        self.__method = method

    def __enter__(self):
        setattr(self.__item,
                self.__method,
                True)

    def __exit__(self, type, value, traceback):
        setattr(self.__item,
                self.__method,
                False)


# class ClassProperty(object):
#     __item = None
#     __property = None
#     __getter = None
#     __setter = None
#     def __init__(self, item, property=None, getter=None, setter=None):
#         self.__item = item
#         self.__property = self.__parseInput(property)
#         self.__getter = self.__parseInput(getter)
#         self.__setter = self.__parseInput(setter)

#     def __parseInput(self, prop):
#         if not prop:
#             return None

#         if not self.__item:
#             raise RuntimeError('No Item specified')

#         if callable(prop):
#             return prop

#         if prop.startswith('__'):
#             return '_{0}{1}'.format(self.__item.__class__.__name__, prop)

#         return prop

#     def get(self):
#         if self.__property:
#             return getattr(self.__item, self.__property)

#         return self.__getter()

#     def set(self, value):
#         if self.__property:
#             return setattr(self.__item, self.__property, value)

#         return self.__setter(value)


class AbstractBaseMixin(object):
    '''
    This class is designed to mix into basic classes for display with a
    QTreeView or QListView or whatever

    To use override:
        def __repr__(self):
            return 'CustomClass("paramater")'

        def getData(self, name):
            return data based on the input column name

        def setData(self, name, value):
            set data based on the input column name

        def createChild(self):
            Return a new instance of this with default paramaters

        self.validDataMembers
            A tuple of valid column names that can be get/set

    Optional Override:
        def __hash__(self):
            for performance

        def getIcon(self):
            return a QIcon to be used

        def getCustomRole(self, model, index, role):
            get custom data for display

    USAGE:
        self.log():
            Log the current hierachy of this item

        self.createChild():
            This is called from the abstract model when adding new members

        self.insertChild(pos, child):
            Used to add existing children

        self.setParent(parent):
            Add this item to a new parent

        self.removeChild(index):
            Remove a child

        self.getParent():
            Get the active parent if available

        self.children():
            an iterator for the children
    '''
    __metaclasss__ = abc.ABCMeta
    def __new__(cls, *args, **kwargs):
        instance = super(AbstractBaseMixin, cls).__new__(cls, *args, **kwargs)
        instance.__children = list()
        instance.__flags = list()
        instance.__parent = None
        instance._internalMove = False
        instance.__internalMover = None
        instance.hasCustomFlags = False
        return instance

    @abc.abstractmethod
    def __repr__(self):
        '''
        Override for use in logging

        :returns: creation command
        :rtype: str
        '''
        pass

    @abc.abstractmethod
    def getData(self, name):
        '''
        Get a datamember by name

        :param str name: name of member
        :returns: result
        :rtype: str
        '''
        pass

    @abc.abstractmethod
    def setData(self, name, value):
        '''
        Set a datamember by name

        :param str name: name of member
        :param str value: value to set
        '''
        pass

    @abc.abstractproperty
    def validDataMembers(self):
        '''
        Return a tuple of strings for valid input to getData

        :returns: Valid Members to Get/Set
        :rtype: tuple
        '''
        pass

    @abc.abstractmethod
    def toStr(self):
        '''
        Output a simple string for this item, like a name

        :returns: string representation
        :rtype: str
        '''
        pass

    @abc.abstractmethod
    def createChild(self):
        '''
        Add a new child to this item

        :returns: Child Item
        :rtype: object
        '''
        pass

    def getIcon(self):
        '''
        Return the icon for this item

        :returns: Icon
        :rtype: QIcon
        '''
        return None

    def getCustomRole(self, model, index, role):
        '''
        Return data for a custom Qt Role

        :param QAbstractItemModel model: Active model
        :param QModelIndex index: Active index
        :param QRole role: Active role
        '''
        return None

    def flags(self):
        '''
        Return Any override flags

        :returns: flags
        :rtype: ItemFlags
        '''
        return self.__flags

    def setFlags(self, flags):
        '''
        Set the flags

        :param ItemFlags flags: item flags
        '''
        self.__flags = flags

    @property
    def internalCallback(self):
        '''
        Used internally to prevent move conflicts
        Usage:
            with item.internalCallback:
                do stuff

        :returns: InternalMoveWrapper item
        :rtype: InternalMoveWrapper
        '''
        if not self.__internalMover:
            self.__internalMover = InternalMoveWrapper(self)

        return self.__internalMover

    def __validateItem(self, item):
        '''
        Used internally to validate items before parenting

        :param object item: item to validate
        :returns: Status
        :rtype: bool
        '''
        if not issubclass(type(item), AbstractBaseMixin):
            return False

        if item in self.__children:
            return False

        return True

    def addChild(self, child):
        '''
        Add a child to this item

        :param object child: child to add
        :returns: success
        :rtype: bool
        '''
        if not self.__validateItem(child):
            return False

        self.__children.append(child)
        if not self._internalMove:
            with child.internalCallback:
                return child.setParent(self)

        return True

    def insertChild(self, pos, child):
        '''
        insert a child to this item

        :param int pos: position to add child to
        :param object child: child to add
        :returns: success
        :rtype: bool
        '''
        if not self.__validateItem(child):
            return False

        if pos is None or pos >= len(self.__children):
            self.__children.append(child)

        else:
            self.__children.insert(pos, child)

        if not child.getParent() == self:
            with child.internalCallback:
                child.setParent(self)
        return True

    def setParent(self, parent):
        '''
        Sets the parent for this item, This will also remove the active parent

        :param object parent: parent to add to
        :returns: success
        :rtype: bool
        '''
        currentParent = self.__parent
        if currentParent == parent:
            return False

        if not parent:
            if not currentParent:
                return False

            self.__parent = None
            if not self._internalMove:
                currentParent.removeChild(self)
            return True

        if self._internalMove:
            self.__parent = parent
            return True

        with parent.internalCallback:
            if parent.addChild(self):
                self.__parent = parent
                return True

            return False

    def removeChild(self, pos):
        '''
        Removes the child at the position

        :param int pos: position to remove
        :raises IndexError: If out of range
        '''
        maxIndex = self.childCount() - 1
        if not (-maxIndex <= pos <= maxIndex):
            msg = '{0}: Position({1}) out of range, count={2}'
            msg = msg.format(self.__class__.__name__, pos, self.childCount())
            raise IndexError(msg)

        item = self.__children.pop(pos)
        if not self._internalMove:
            with item.internalCallback:
                item.setParent(None)

    def getParent(self):
        '''
        Returns the parent

        :returns: parent
        :rtype: object
        '''
        return self.__parent

    def getChild(self, pos):
        '''
        Get the child at the index

        :param int pos: index
        :returns: child
        :rtype: object
        '''
        maxIndex = self.childCount() - 1
        if not (-maxIndex <= pos <= maxIndex):
            return None

        return self.__children[pos]

    def childCount(self):
        '''
        Get the number of children

        :returns: child count
        :rtype: int
        '''
        return len(self.__children)

    def children(self):
        '''
        Iterator to iterate through children

        :returns: yield child
        :rtype: object
        '''
        for child in self.__children:
            yield child

    def log(self, tabIndex=0):
        '''
        logger for diagnostics, prints the hierachy

        :param int tabIndex: initial tab index
        :returns: log string
        :rtype: str
        '''
        log = ('\t'*tabIndex)+self.__repr__()
        for child in self.children():
            log += '\n'+child.log(tabIndex+1)

        return log


class TextItem(AbstractBaseMixin):
    '''
    Basic Text item for use in the AbstractItemModel

    validDataMembers: ("name")

    :param str text: the text to display
    '''
    validDataMembers = ('name')
    def __init__(self, text):
        self.text = str(text)

    def __hash__(self):
        return hash(self.__repr__())

    def __repr__(self):
        return 'TextItem("{0}")'.format(self.toStr())

    def toStr(self):
        '''
        Returns the contained text

        :returns: self.text
        :rtype: str
        '''
        return str(self.text)

    def getData(self, name):
        '''
        Returns the contained text

        :param str name: member to query
        :returns: self.text
        :rtype: str
        :raises KeyError: For invalid keys
        '''
        if name == 'name':
            return self.text

        raise KeyError('{0}: Invalid Key {1}'.format(self.__class.__name__, name))

    def setData(self, name, value):
        '''
        Sets the text to a new value

        :param str name: member to set
        :param str value: text to set
        :raises KeyError: For invalid keys
        '''
        if name == 'name':
            self.text = str(value)

        raise KeyError('{0}: Invalid Key {1}'.format(self.__class.__name__, name))

    def createChild(self):
        '''
        Adds a new TextItem as a child

        :returns: TextItem('Untitled')
        :rtype: TextItem
        '''
        child = TextItem('Untitled')
        self.addChild(child)
        return child


class RootItem(AbstractBaseMixin):
    '''
    Standard root item, this has no purpose but to contain other items
    This item contains no validDataMembers
    '''
    validDataMembers = tuple()
    def __init__(self):
        pass

    def __hash__(self):
        return hash('ROOT')

    def __repr__(self):
        return 'RootItem()'

    def toStr(self):
        return str('ROOT')

    def getData(self, name):
        return

    def setData(self, name, value):
        return

    def createChild(self):
        '''
        Adds a new TextItem as a child

        :returns: TextItem('Untitled')
        :rtype: TextItem
        '''
        child = TextItem('Untitled')
        self.addChild(child)
        return child



class AbstractItemModel(QtCore.QAbstractItemModel):
    '''
    Basic QAbstractItemModel to work with AbstractBaseMixin types
    headerData can either be a list, or a dictionary of {name: targetName}
    in the instance that you need to rename columns

    :param parent: parent to add to
    :type parent: QWidget or None
    :param headerData: headers to add
    :type headerData: list, tuple or dict
    :param root: Root item
    :type root: AbstractBaseMixin or None
    '''
    def __init__(self, parent=None, headerData=None, root=None):
        super(AbstractItemModel, self).__init__(parent)

        if root:
            self.__root = root

        if not headerData:
            self.setHeaders(self.__defaultHeaderData)

        else:
            self.setHeaders(headerData)

    def __new__(cls, *args, **kwargs):
        instance = super(AbstractItemModel, cls).__new__(cls, *args, **kwargs)
        instance.__headerData = {}
        instance.__defaultHeaderData = OrderedDict(name=None)
        instance.__flags = QtCore.Qt.ItemIsEnabled
        instance.__flags |= QtCore.Qt.ItemIsSelectable
        instance.__flags |= QtCore.Qt.ItemIsEditable
        instance.__headers = []
        instance.__headersCache = {}
        instance.__root = RootItem()
        instance.__forceFlags = False
        return instance

    def setHeaders(self, headerData):
        '''
        Set the headerdata for this model

        :param headerData: headers to add
        :type headerData: list, tuple or dict
        '''
        if isType(headerData, [list, set, tuple]):
            headerData = OrderedDict(((item, None) for item in headerData))

        self.__headerData = headerData
        self.__headers = headerData.keys()
        self.__headersCache = dict()

    def flags(self, index):
        '''
        Return the flags an index, if force flags is not set it will use
        the items own flags if it has them
        If index is None, it will return the model flags

        :param QModelIndex index: index to query
        :returns: flags
        :rtype: ItemFlags
        '''
        if index is None or self.__forceFlags:
            return self.__flags

        if not index.isValid():
            return self.__flags

        item = index.internalPointer()
        if item.hasCustomFlags:
            return item.flags()

        return self.__flags

    def setFlags(self, flags):
        '''
        Set the flags for this model

        :param ItemFlags flags: flags to set
        '''
        self.__flags = flags

    def getRoot(self):
        '''
        Get the root item

        :returns: internal root item
        :rtype: RootItem
        '''
        return self.__root

    def setRoot(self, item):
        '''
        Set the root item

        :param RootItem item: root
        '''
        self.__root = item

    def setForceFlags(self, force=False):
        '''
        Enable or disable forceFlags

        :param bool force: state
        '''
        self.__forceFlags = force

    def rowCount(self, parent):
        '''
        Return number of rows for the item

        :param QModelIndex parent: index to query
        :returns: number of rows
        :rtype: int
        '''
        if parent.isValid():
            item = parent.internalPointer()

        else:
            item = self.__root

        return item.childCount()

    def columnCount(self, parent):
        '''
        Return number of columns for the item

        :param QModelIndex parent: index to query
        :returns: number of columns
        :rtype: int
        '''
        return len(self.__headers)

    def __retrieveHeader(self, column):
        '''
        Internal function, retrieve the real header name

        :param int column: column index
        :returns: column name
        :rtype: str
        '''
        header = self.__headers[column]
        if header not in self.__headersCache:
            headerMap = self.__headerData[header]
            self.__headersCache[header] = headerMap or header

        return self.__headersCache[header]

    def getItemProperty(self, item, column):
        '''
        Gets the member for the item based on the column index

        :param object item: item to query
        :param int column: column index
        :returns: item data
        :rtype: str
        '''
        header = self.__retrieveHeader(column)
        if header not in item.validDataMembers:
            return None

        return item.getData(header)

    def setItemProperty(self, item, column, value):
        '''
        Sets the member for the item based on the column index

        :param object item: item to query
        :param int column: column index
        :param str value: value to set
        '''
        header = self.__retrieveHeader(column)
        if header not in item.validDataMembers:
            return None

        return item.setData(header, value)

    def data(self, index, role):
        if not index.isValid():
            return None

        item = index.internalPointer()
        if item == self.getRoot():
            return None

        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            prop = self.getItemProperty(item, index.column())
            if prop is None:
                return 'None'

            return str(prop)

        elif role == QtCore.Qt.DecorationRole:
            return item.getIcon()

        else:
            return item.getCustomRole(self, index, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.isValid() and role == QtCore.Qt.EditRole:
            item = index.internalPointer()
            result = self.setItemProperty(item, index.column(), value)
            return bool(result)

        return False

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            return self.__headers[section]

    def headers(self):
        '''
        Return the current headers

        :returns: header list
        :rtype: list
        '''
        return self.__headers

    def parent(self, index):
        item = self.getItem(index)
        parentItem = item.getParent()

        if not parentItem or parentItem == self.__root:
            return QtCore.QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def index(self, row, column, parent):
        if isinstance(parent, QtCore.QModelIndex):
            parent = self.getItem(parent)

        childItem = parent.getChild(row)

        if childItem:
            return self.createIndex(row, column, childItem)

        else:
            return QtCore.QModelIndex()

    def getItem(self, index):
        '''
        Return the internal item at the index

        :param QModelIndex index: index to query
        :returns: Item object
        :rtype: object
        '''
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.__root

    def createChild(self, parentItem=None):
        '''
        Create a new child under the parent item
        simply calls parent.createChild() while maintaining the model

        :param parentItem: item to add to
        :type parentItem: QModelIndex or AbstractBaseMixin or None
        :returns: New child
        :rtype: object
        '''
        rootNode, _ = self.beginInsertion(1, None, parentItem)
        parent = parentItem or rootNode
        item = parent.createChild()
        self.endInsertRows()
        return item

    def beginInsertion(self, rows, position, parent):
        '''
        Internal utility to help inserting from multiple calls

        :param int rows: number of rows to add
        :param int position: position to start adding
        :param parent: parent to add to
        :type parent: QModelIndex or AbstractBaseMixin or None
        :returns: tuple(parentNode, position)
        :rtype: tuple
        '''
        if isinstance(parent, QtCore.QModelIndex):
            parentNode = self.getItem(parent)

        if parent is None:
            parent = QtCore.QModelIndex()
            parentNode = self.__root

        if position is None:
            position = parentNode.childCount()

        position = parentNode.childCount() if position is None else position

        self.beginInsertRows(parent, position, int(position) + rows - 1)
        return (parentNode, position)

    def insertRows(self, items, position=None, parent=None):
        '''
        Add new rows to the model

        :param list items: items to add
        :param int position: position to start adding
        :param parent: parent to add to
        :type parent: QModelIndex or AbstractBaseMixin or None
        :returns: Success
        :rtype: bool
        '''
        parentNode, position = self.beginInsertion(len(items), position, parent)
        success = True
        for item in items:
            success *= parentNode.insertChild(position, item)
            position += 1

        self.endInsertRows()
        return bool(success)

    def endInsertion(self):
        self.endInsertRows()

    def removeRows(self, position, rows, parent=None):
        '''
        Remove rows from the model

        :param int position: position to start adding
        :param int rows: number of rows to remove
        :param QModelIndex parent: parent to remove from
        :returns: Success
        :rtype: bool
        '''
        if parent is None:
            parent = QtCore.QModelIndex()

        parentNode = self.getItem(parent)
        self.beginRemoveRows(parent, position, position + rows - 1)

        for row in xrange(rows):
            success = parentNode.removeChild(position)

        self.endRemoveRows()

        return success

    def removeIndex(self, index):
        '''
        Remove an index from the model

        :param QModelIndex index: index to remove
        '''
        parent = index.parent()
        if not parent.isValid():
            parent = QtCore.QModelIndex()

        self.removeRows(index.row(), 1, parent)


class SimpleListWidget(QtGui.QWidget):
    '''
    Simple list widget to display items from the AbstractItemModel

    :param str label: header label
    :param dict headerData: display headers
    :param object root: Optional root item
    '''
    def __init__(self, label, headerData=None, root=None):
        super(SimpleListWidget, self).__init__()
        self.__labelText = label
        self.__headerData = headerData or ['name']
        self.__root = root

        self.buildUI()
        self.connectUI()

    def buildUI(self):
        '''
        Construct the interface
        '''
        self.mainLayout = QtGui.QVBoxLayout()
        self.setLayout(self.mainLayout)
        self.mainLayout.setContentsMargins(0, 0, 0, 0)

        headerLayout = addWidget(QtGui.QHBoxLayout, None, self.mainLayout)
        headerLayout.setContentsMargins(0, 0, 0, 0)
        self.label = addWidget(QtGui.QLabel, 'listLabel',
                               headerLayout, self.__labelText)

        headerLayout.addStretch(1)
        self.btnAdd = addWidget(QtGui.QPushButton, 'btnAdd',
                                headerLayout, '[+]')
        self.btnRemove = addWidget(QtGui.QPushButton, 'btnRemove',
                                   headerLayout, '[-]')

        self.view = addWidget(QtGui.QListView, 'listView', self.mainLayout)
        model = AbstractItemModel(self, self.__headerData, root=self.__root)
        self.view.setModel(model)

    def connectUI(self):
        '''
        Perform callback connections
        '''
        self.btnAdd.clicked.connect(self.btnAddCB)
        self.btnRemove.clicked.connect(self.btnRemoveCB)

    @property
    def model(self):
        '''
        Return the current model

        :returns: self.view.model()
        :rtype: AbstractItemModel
        '''
        return self.view.model()

    def selectedIndex(self):
        '''
        Return the selected index

        :returns: selected index
        :rtype: QModelIndex
        '''
        return self.view.selectionModel().currentIndex()

    def addItems(self, items):
        '''
        Add items to the model

        :param list items: items to add
        '''
        self.model.insertRows(items)

    def btnAddCB(self):
        '''
        Add a new item to the model
        '''
        self.model.createChild()

    def btnRemoveCB(self):
        '''
        Remove the selected item from the model
        '''
        index = self.selectedIndex()
        self.model.removeIndex(index)

# example
# items = [TextItem(a) for a in 'This is a test to see if this works'.split()]

# w = SimpleListWidget('Header')
# w.addItems(items)
# w.show()

