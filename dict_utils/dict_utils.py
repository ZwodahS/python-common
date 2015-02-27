# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Author : Eric (github.com/ZwodahS)
# License : Public Domain

def dict_filter(data, include=None, exclude=None, include_only=False, preserve_empty_values=True):
    """
    Takes in a data in the form of dictionary, returns a new dictionary that match the criteria

    kwargs
        data                        The dictionary data

        include                     The fields (list) to includes.

        exclude                     The fields (list) to excludes.

        include_only                If True, then only those included will be returned.

        preserve_empty_values       If False, all empty dictionary will be filtered.

        The order of operations differs based include_only

        If include_only is True
            start with an empty list
            . for each field in the include_list, add it into the output list.
            . if a field exist in exclude and include at the same time, excludes takes priority.
            . The more specific case takes priority.

        If include_only is False
            start with everything,

    """
    def _fields_dict_filter(fields):
        '''
        Separate a list of fields to a set of non-subdocumented fields and a dictionary
        whose keys are the subdocuments and values are lists of their fields.

        Example:
            fields = ["email", "address", "address.coordinates"]
            Return : {"email", "address"} { "address" : [ "coordinates" ] }
        '''
        output_fields = set()
        output_dict = {}

        if isinstance(fields, list):
            for field in fields:

                if '.' in field:
                    split = field.split(".")
                    if not split[0] in output_dict:
                        output_dict[split[0]] = []

                    output_dict[split[0]] += [".".join(split[1:])]

                else:
                    output_fields |= {field}

        return output_fields, output_dict

    def _internal_filter(_data, _include, _exclude, _use_self_keys):
        """
        keep include_only as a fixed value and use _use_self_keys as the dynamic one.
        """
        if type(_data) not in [dict, list]:
            return _data if _use_self_keys else None

        if isinstance(_data, list):
            t = [ _internal_filter(_d, _include, _exclude, _use_self_keys) for _d in _data ]
            t = [ v for v in t if preserve_empty_values or v ]
            return t

        include_fields, include_dict = _fields_dict_filter(_include)
        exclude_fields, exclude_dict = _fields_dict_filter(_exclude)

        keys = ((set() if not _use_self_keys else set(_data.keys())) | include_fields) - exclude_fields
        out = {}

        for k in keys:
            if k in _data:
                value = None
                if k in exclude_dict and type(_data[k]) in [list, dict]:
                    value = _internal_filter(_data[k], include_dict.get(k, []), exclude_dict.get(k), True)
                else:
                    value = _data[k]

                if preserve_empty_values or value:
                    out[k] = value

        for k in include_dict:
            if k in _data and not k in out:
                value = _internal_filter(_data[k], include_dict.get(k), exclude_dict.get(k, []), False)
                if preserve_empty_values or value:
                    out[k] = value

        return out

    return _internal_filter(data, include, exclude, not include_only)


def dict_project(data, projections):
    """
    Takes in a dictionary, project the fields from one fields to another, and adding default values if they are missing
    The actual data is modifed.

    data                The dictionary object
    projections         list of projection in the following format
                        (<original field>, <target field>, default_value[optional])
                        <original field>,<target field> in the format field.field (i.e address.block_number)

                        if default_value is omitted, then there will be no default value set if the value do not exist in the
                        original field
    """
    def _find_value_and_unset(_data, _fields):
        if len(_fields) == 1:
            if type(_data) == dict and _fields[0] in _data:
                value = _data[_fields[0]]
                del _data[_fields[0]]
                return value, True
            else:
                return None, False
        else:
            if _fields[0] in _data:
                if type(_data[_fields[0]]) == dict:
                    value, found = _find_value_and_unset(_data[_fields[0]], _fields[1:])
                    if len(_data[_fields[0]]) == 0:
                        del _data[_fields[0]]
                    return value, found
            else:
                return None, False

    def _find_and_set(_data, _fields, value):
        if len(_fields) == 1:
            if _fields[0] != '':
                _data[_fields[0]] = value
        else:
            if _fields[0] not in _data:
                _data[_fields[0]] = {}
                _find_and_set(_data[_fields[0]], _fields[1:], value)
            else:
                if type(_data[_fields[0]])!= dict:
                    return # do not try to set anything
                else:
                    _find_and_set(_data[_fields[0]], _fields[1:], value)

    for p in projections:
        original_field = p[0].split(".")
        target_field = p[1].split(".")
        value, found = _find_value_and_unset(data, original_field)
        if found:
            _find_and_set(data, target_field, value)
        elif len(p) == 3:
            _find_and_set(data, target_field, p[2])

    return data

def dict_equal(d1, d2):
    """
    recursively check if 2 dictionary is the same.
    """
    if type(d1) != type(d2):
        return False

    if isinstance(d1, dict) and isinstance(d2, dict):
        set_all = set(d1.keys() + d2.keys())
        for k in set_all:
            if k not in d1 or k not in d2:
                return False
            if not dict_equal(d1.get(k), d2.get(k)):
                return False

    if isinstance(d1, list) and isinstance(d2, list):
        if len(d1) != len(d2):
            return False

        return all([dict_equal(d[0], d[1]) for d in zip(d1, d2)])

    return d1 == d2


def dict_combine(d1, d2): # d1 + d2, conflicting keys will be taken from d1
    d3 = { k:v for k,v in d2.iteritems() }
    d3.update(d1)
    return d3


if __name__ == "__main__":
    import copy
    import pprint
    # test_data = {
    #         'a' : { 'b' : 1, 'c' : 2, 'd' : 3},
    #         'b' : [ 1, 2, 3, 4 ],
    #         'c' : [ {'a' : { 'b' : 1 }, 'b' : {'a' : 1 } }, {'a' : { 'b' : 2, 'c' : 3} } ]
    #         'd' : { 'a' : 1, 'b' : { 'c' : 1 } }
    #         }
    test_data={'a':{'b':1,'c':2,'d':3},'b':[1,2,3,4],'c':[{'a':{'b':1},'b':{'a':1}},{'a':{'b':2,'c':3}}],'d':{'a':1,'b':{'c':1}}}

    # test case : (title, query, expectation)
    TESTS = [
        ('thingalwaysreturneverything', {}, {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('include_onlyreturnsnothing', {'include_only':True}, {}), 
        ('preservationofemptylist', {'exclude':['c.a', 'c.b']}, {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{}, {}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('non-preservationofemptylist', {'exclude':['c.a', 'c.b'], 'preserve_empty_values':False}, {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'd':{'a':1, 'b':{'c':1}}}), 
        ('excludesinglefieldinroot', {'exclude':['a']}, {'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('excludenestedfield', {'exclude':['a.b']}, {'a':{'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('excludemultiplenestedfields', {'exclude':['a.b', 'a.c']}, {'a':{'d':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('excludenestedfieldinlistdictionary', {'exclude':['c.b']}, {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('excludenotaffectingnon-matching', {'exclude':['b.a']}, {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('includeinnerfieldwhileexcludingouterfield', {'exclude':['a'], 'include':['a.b']}, {'a':{'b':1}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}), 
        ('includerootwheninclude_only', {'include_only':True, 'include':['a']}, {'a':{'b':1, 'c':2, 'd':3}}), 
        ('includenested_fieldswheninclude_only', {'include_only':True, 'include':['a.b']}, {'a':{'b':1}, }), 
        ('includefieldsinlistwheninclude_only', {'include_only':True, 'include':['c.a']}, {'c':[{'a':{'b':1}}, {'a':{'b':2, 'c':3}}]}), 
        ('excludeinnerfieldwhileincludingouterfield', {'include_only':True, 'include':['a'], 'exclude':['a.b']}, {'a':{'c':2, 'd':3}}), 
    ]

    pp = pprint.PrettyPrinter(indent=4)
    tests1 = [0, 0, 0]
    for test in TESTS:
        result = dict_filter(test_data, **test[1])
        expectation = test[2]
        matched = dict_equal(result, expectation)
        print("Test ({0}) Result : {1}".format(test[0], "Pass" if matched else "Failed"))
        if matched:
            tests1[0]+=1
        else:
            tests1[1]+=1
        tests1[2]+=1
        if not matched:
            print("Expectation : ")
            pp.pprint(expectation)
            print("Found : ")
            pp.pprint(result)

    TESTS = [
        ('noprojectionreturnsitself', [], {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}),
        ('singleprojectonasinglefield', [('a.c', 'abc')], {'a':{'b':1, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'abc':2, 'd':{'a':1, 'b':{'c':1}}}),
        ('projectiononadictionary', [('a', 'a-copy')], {'a-copy':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}),
        ('testnodefaultvalue', [('a.e', 'e')], {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}),
        ('testdefaultvalue', [('a.e', 'e', 0)], {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}, 'e':0}),
        ('projectiononexistingfieldswillreplace', [('a.b', 'b')], {'a':{'c':2, 'd':3}, 'b':1, 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}),
        ('projectiononinnerfieldwhenouterisnotdict', [('a.b', 'b.b')], {'a':{'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1, 'b':{'c':1}}}),
        ('projectionwilldestroyemptydictionary', [('d.b.c', 'e')], {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1}, 'e':1}),
        ('projectionwithemptytargetfiltersit', [('d.b', '')], {'a':{'b':1, 'c':2, 'd':3}, 'b':[1, 2, 3, 4], 'c':[{'a':{'b':1}, 'b':{'a':1}}, {'a':{'b':2, 'c':3}}], 'd':{'a':1}}),
    ]
    tests2 = [0, 0, 0]
    for test in TESTS:
        temp = copy.deepcopy(test_data)
        dict_project(temp, test[1])
        expectation = test[2]
        matched = dict_equal(temp, expectation)
        print("Test ({0}) Result : {1}".format(test[0], "Pass" if matched else "Failed"))
        if matched:
            tests2[0]+=1
        else:
            tests2[1]+=1
        tests2[2]+=1
        if not matched:
            print("Expectation : ")
            pp.pprint(expectation)
            print("Found : ")
            pp.pprint(temp)

    print("dict_filters tests Passed : {0}, Failed : {1}, Total : {2}".format(tests1[0], tests1[1], tests1[2]))
    print("dict project tests Passed : {0}, Failed : {1}, Total : {2}".format(tests2[0], tests2[1], tests2[2]))
