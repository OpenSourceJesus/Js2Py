from ..base import *
import six

#todo Double check everything is OK


@Js
def Object():
    val = arguments.get('0')
    if val.is_null() or val.is_undefined():
        return PyJsObject(prototype=ObjectPrototype)
    return val.to_object()


@Js
def object_constructor():
    if len(arguments):
        val = arguments.get('0')
        if val.TYPE == 'Object':
            #Implementation dependent, but my will simply return :)
            return val
        elif val.TYPE in ('Number', 'String', 'Boolean'):
            return val.to_object()
    return PyJsObject(prototype=ObjectPrototype)


Object.create = object_constructor
Object.own['length']['value'] = Js(1)


class ObjectMethods:
    def getPrototypeOf(obj):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.getPrototypeOf called on non-object')
        return null if obj.prototype is None else obj.prototype

    def getOwnPropertyDescriptor(obj, prop):
        if not obj.is_object():
            raise MakeError(
                'TypeError',
                'Object.getOwnPropertyDescriptor called on non-object')
        return obj.own.get(
            prop.to_string().
            value)  # will return undefined if we dont have this prop

    def getOwnPropertyNames(obj):
        if not obj.is_object():
            raise MakeError(
                'TypeError',
                'Object.getOwnPropertyDescriptor called on non-object')
        return obj.own.keys()

    def create(obj):
        if not (obj.is_object() or obj.is_null()):
            raise MakeError('TypeError',
                            'Object prototype may only be an Object or null')
        temp = PyJsObject(prototype=(None if obj.is_null() else obj))
        if len(arguments) > 1 and not arguments[1].is_undefined():
            if six.PY2:
                ObjectMethods.defineProperties.__func__(temp, arguments[1])
            else:
                ObjectMethods.defineProperties(temp, arguments[1])
        return temp

    def defineProperty(obj, prop, attrs):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.defineProperty called on non-object')
        name = prop.to_string().value
        if not obj.define_own_property(name, ToPropertyDescriptor(attrs)):
            raise MakeError('TypeError', 'Cannot redefine property: %s' % name)
        return obj

    def defineProperties(obj, properties):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.defineProperties called on non-object')
        props = properties.to_object()
        for name in props:
            desc = ToPropertyDescriptor(props.get(name.value))
            if not obj.define_own_property(name.value, desc):
                raise MakeError(
                    'TypeError',
                    'Failed to define own property: %s' % name.value)
        return obj

    def seal(obj):
        if not obj.is_object():
            raise MakeError('TypeError', 'Object.seal called on non-object')
        for desc in obj.own.values():
            desc['configurable'] = False
        obj.extensible = False
        return obj

    def freeze(obj):
        if not obj.is_object():
            raise MakeError('TypeError', 'Object.freeze called on non-object')
        for desc in obj.own.values():
            desc['configurable'] = False
            if is_data_descriptor(desc):
                desc['writable'] = False
        obj.extensible = False
        return obj

    def preventExtensions(obj):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.preventExtensions on non-object')
        obj.extensible = False
        return obj

    def isSealed(obj):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.isSealed called on non-object')
        if obj.extensible:
            return False
        for desc in obj.own.values():
            if desc['configurable']:
                return False
        return True

    def isFrozen(obj):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.isFrozen called on non-object')
        if obj.extensible:
            return False
        for desc in obj.own.values():
            if desc['configurable']:
                return False
            if is_data_descriptor(desc) and desc['writable']:
                return False
        return True

    def isExtensible(obj):
        if not obj.is_object():
            raise MakeError('TypeError',
                            'Object.isExtensible called on non-object')
        return obj.extensible

    def keys(obj):
        if not obj.is_object():
            raise MakeError('TypeError', 'Object.keys called on non-object')
        return [e for e, d in six.iteritems(obj.own) if d.get('enumerable')]

    def values(obj):
        if not obj.is_object():
            raise MakeError('TypeError', 'Object.values called on non-object')
        return [obj.get(k) for k, d in six.iteritems(obj.own)
                if d.get('enumerable')]

    def entries(obj):
        if not obj.is_object():
            raise MakeError('TypeError', 'Object.entries called on non-object')
        return [[Js(k), obj.get(k)] for k, d in six.iteritems(obj.own)
                if d.get('enumerable')]

    def assign(target):
        if not target.is_object():
            raise MakeError('TypeError', 'Object.assign target must be an object')
        obj = target.to_object()
        for i in range(1, len(arguments)):
            src = arguments[i]
            if src.is_null() or src.is_undefined():
                continue
            src_obj = src.to_object()
            for name, desc in six.iteritems(src_obj.own):
                if desc.get('enumerable'):
                    obj.put(name, src_obj.get(name))
        return obj

    def fromEntries(iterable):
        obj = PyJsObject(prototype=ObjectPrototype)
        items = iterable.to_object()
        length = items.get('length')
        if length.TYPE == 'Number':
            count = length.to_uint32()
            for i in range(count):
                entry = items.get(str(i))
                if entry.TYPE != 'Object':
                    raise MakeError('TypeError', 'Invalid entry in fromEntries')
                key = entry.get('0')
                val = entry.get('1')
                obj.put(key.to_string().value, val)
            return obj
        raise MakeError('TypeError', 'Object.fromEntries requires an iterable')

    def hasOwn(obj, prop):
        if not obj.is_object():
            raise MakeError('TypeError', 'Object.hasOwn called on non-object')
        return prop.to_string().value in obj.own


# add methods attached to Object constructor
fill_prototype(Object, ObjectMethods, default_attrs)
# add constructor to prototype
fill_in_props(ObjectPrototype, {'constructor': Object}, default_attrs)
# add prototype property to the constructor.
Object.define_own_property(
    'prototype', {
        'value': ObjectPrototype,
        'enumerable': False,
        'writable': False,
        'configurable': False
    })

# some utility functions:


def ToPropertyDescriptor(obj):  # page 38 (50 absolute)
    if obj.TYPE != 'Object':
        raise MakeError('TypeError',
                        'Can\'t convert non-object to property descriptor')
    desc = {}
    if obj.has_property('enumerable'):
        desc['enumerable'] = obj.get('enumerable').to_boolean().value
    if obj.has_property('configurable'):
        desc['configurable'] = obj.get('configurable').to_boolean().value
    if obj.has_property('value'):
        desc['value'] = obj.get('value')
    if obj.has_property('writable'):
        desc['writable'] = obj.get('writable').to_boolean().value
    if obj.has_property('get'):
        cand = obj.get('get')
        if not (cand.is_undefined() or cand.is_callable()):
            raise MakeError(
                'TypeError',
                'Invalid getter (it has to be a function or undefined)')
        desc['get'] = cand
    if obj.has_property('set'):
        cand = obj.get('set')
        if not (cand.is_undefined() or cand.is_callable()):
            raise MakeError(
                'TypeError',
                'Invalid setter (it has to be a function or undefined)')
        desc['set'] = cand
    if ('get' in desc or 'set' in desc) and ('value' in desc
                                             or 'writable' in desc):
        raise MakeError(
            'TypeError',
            'Invalid property.  A property cannot both have accessors and be writable or have a value.'
        )
    return desc
