from erm.core.models import *
from erm.datamanager.models import *
from erm.lib.misc_utils import *
from erm.lib.api import ApiError, ERROR_CODES
from erm.core.entity_manager import *

from django.core.exceptions import ObjectDoesNotExist
from django.db.models.query import EmptyQuerySet
from django.db import connection, DatabaseError, IntegrityError, transaction

from urllib import unquote

import datetime

#ERROR_CODES=dict()
#=====================generic or common errors=====================#
ERROR_CODES["10000"]="series manager: Generic error"

DAYS_CHUNKS_SEP='-'

#===============SERIES TODAY=============#

def get_series_today(params):
    try:
        series=list()
        _series_objs = SeriesToday.objects.filter(day=datetime.date.today())
        if params.get('name', "")!="":
            _series_objs = SeriesToday.objects.filter(name=params.get('name'))
            
        if len(_series_objs):
            for _series_obj in _series_objs:
                _series=_series_obj.to_dict()        
                list_offset=max(int(params.get('offset', 0)),0)
                list_limit=max(int(params.get('limit', 20)),1)
                if list_limit!=0:
                    _series['values']=_series['values'][list_offset: list_offset+list_limit]
                series.append(_series)
        return series

    except Exception, err:
       raise ApiError(None, 10000, err)

def add_series_today(params):
    try:
        _counter=0
        _result=list()
        for _name, _values in params.get('series', dict()).items():
            series_obj, series_created = SeriesToday.objects.get_or_create(name=_name,
                                                                           day=datetime.date.today())
            if series_created:
                series_obj.values=_values
            else:
                series_obj.values=series_obj.values+SeriesDict(_values)
            series_obj.save()
            
            add_series_current({"name":_name, "values":_values})
            _counter+=1
            _result.append(series_obj.to_dict())
        return _result
    except Exception, err:
        raise ApiError(None, 10000, err)

def del_series_today(params):
    if params.get('archive', "")=="1":
        _counters=[0,0]
        _old_series_list=SeriesToday.objects.filter(day__lt=datetime.date.today())
        Logger().log('Going to archive old data: %s' % _old_series_list.values('name', 'day'))
        try:
            for _old_series in _old_series_list:
                try:
                    _history_series=SeriesHistory.objects.get(name=_old_series.name,
                                                              day=_old_series.day)
                except ObjectDoesNotExist, err:
                    _history_series=SeriesHistory(name=_old_series.name,
                                                  day=_old_series.day)
                _history_series.json_values=_old_series.json_values
                _history_series.save()
                _old_series.delete()
                _counters[0]+=1
        except Exception, err:
            raise ApiError(None, 10000, err)
        try:
            for _curr_series in SeriesCurrent.objects.all():
                _curr_series.trim()
                _counters[1]+=1
        except Exception, err:
            raise ApiError(None, 10000, err)
        return _counters
    else:
        try:
            series_obj=SeriesToday.objects.get(name=params.get('name'), 
                                                     day=datetime.date.today())
            series_obj.delete()
        except ObjectDoesNotExist, err:
            pass
        except Exception, err:
            raise ApiError(None, 10000, err)
    
#===============SERIES CURRENT=============#

def calc_current(name, length):
    _values=SeriesDict()
    _limit_date=datetime.date.today()-datetime.timedelta(hours=24*(length-1))
    series_history_objects=SeriesHistory.objects.filter(
                                                        name=name,
                                                        day__gte=_limit_date
                                                        )
    for series_day in series_history_objects:
        _values=_values+series_day.values
    
    try:
        series_today = SeriesToday.objects.get(name=name, 
                        day=datetime.date.today()
                        )
        _values = _values+series_today.values
    except ObjectDoesNotExist, err:
        pass
    return _values


def get_series_current(params):
    _name=params.get('name')
    _length=int(params.get('length'))
    list_offset=max(int(params.get('offset', 0)),0)
    list_limit=max(int(params.get('limit', 20)),1)
    try:
        series_obj=SeriesCurrent.objects.get(name=_name, 
                                             length=_length
                                            )       
        
        if params.get('trim', "0") == "1":
            series_obj.trim()
        
        series=series_obj.to_dict()        
        if list_limit!=0:
            series['values']=series['values'][list_offset: list_offset+list_limit]

        return series

    except ObjectDoesNotExist, err:
        if bool(int(params.get('add',0))):
            
            add_params = {'name': _name,
                       'length': "%s" % _length}
            add_series_rule(add_params)
            
            get_params = {'name': _name,
                       'length': _length,
                       'offset': list_offset,
                       'limit':list_limit}
            
            return get_series_current(get_params)

        elif bool(int(params.get('force',0))):
            _values=calc_current(_name, _length)
            _limit_date=datetime.date.today()-datetime.timedelta(hours=24*(_length-1))
            
            _values=_values.to_sorted_list('value', True)
            if list_limit!=0:
                _values=_values[list_offset: list_offset+list_limit]

            
            return dict(name = _name,
                       values = _values,
                       day = "%s" % _limit_date,
                       length = _length
                   )
        else:
            raise ApiError(None, 10000, "No series current defined for required params (%s) [%s]" % (params, err))
            return dict(name = _name,
                       values = dict(),
                       day = "%s" % datetime.date.today(),
                       length = _length
                   )
    except Exception, err:
       raise ApiError(None, 10000, err)

def add_series_current(params):
    try:
        _name=params.get('name')
        _values=SeriesDict(params.get('values'))
        series_rules=SeriesRule.objects.filter(name=_name)
        for _rule in series_rules:
            series_obj, series_created=SeriesCurrent.objects.get_or_create(
                                                                name=_name,
                                                                length = _rule.length
                                                                )
            if series_created:
                series_obj.day_trimmed = datetime.date.today()
            series_obj.values=series_obj.values+_values
            series_obj.save()
    except Exception, err:
        raise ApiError(None, 10000, err)

def del_series_current(params):
    try:
        _name=params.get('name')
        _length=params.get('length')
        SeriesCurrent.objects.get(name=_name, 
                                day=datetime.date.today(),
                                length=_length
                                ).delete()    
    except ObjectDoesNotExist, err:
        pass
    except Exception, err:
        raise ApiError(None, 10000, err)

#===============SERIES History=============#

def get_series_history(params):
    try:
        series_obj=SeriesHistory.objects.filter(name=params.get('name'))
        if params.get('day', "")!="":
            _day=datetime.date(*(int(n) for n in params.get('day').split(DAYS_CHUNKS_SEP)))
            series_obj=series_obj.filter(day=_day)
        if params.get('range', "")!="":
            _start, _end=params.get('range').split(',')
            
            if _start!="":
                _start_day=datetime.date(*(int(n) for n in _start.split(DAYS_CHUNKS_SEP)))
                series_obj=series_obj.filter(day__gte=_start_day)
            if _end!="":
                _end_day=datetime.date(*(int(n) for n in _end.split(DAYS_CHUNKS_SEP)))
                series_obj=series_obj.filter(day__lte=_end_day)

        result_series=list()     
        
        list_offset=max(int(params.get('offset', 0)),0)
        list_limit=max(int(params.get('limit', 20)),1)
        
        if len(series_obj):
            for _series in series_obj:
                if list_limit!=0:
                    _series_dict=_series.to_dict()
                    _series_dict['values']=_series_dict['values'][list_offset: list_offset+list_limit]
                    result_series.append(_series_dict)
        return result_series

    except Exception, err:
       raise ApiError(None, 10000, err)

def add_series_history(params):
    try:
        _name = params.get('name')
        _day = datetime.date(*(int(n) for n in params.get('day').split(DAYS_CHUNKS_SEP)))
        series_obj, series_created=SeriesHistory.objects.get_or_create(name = _name,
                                                                       day = _day)
        series_obj.values=params.get('values', dict())
        
        series_obj.save()
        
        return series_obj.to_dict()
    except Exception, err:
        raise ApiError(None, 10000, err)

def del_series_history(params):
    try:
        _name = params.get('name')
        _day = datetime.date(*(int(n) for n in params.get('day').split(DAYS_CHUNKS_SEP)))
        series_obj=SeriesHistory.objects.get(name=_name, 
                                           day=_day)
        series_obj.delete()
    except ObjectDoesNotExist, err:
        pass
    except Exception, err:
        raise ApiError(None, 10000, err)
    
#===============SERIES RULES=============#

def get_series_rule(params):
    try:
        series_obj=SeriesRule.objects.all()
        if params.get('name', "")!="":
            series_obj=series_obj.filter(name=params.get('name'))
        if params.get('length', "")!="":
            _lengths = (int(_item) for _item in params.get('length').split(','))
            series_obj=series_obj.filter(length__in=_lengths)
        if params.get('count', "0")=="1":
            return len(series_obj)
        else:
            return list(series_obj)

    except Exception, err:
       raise ApiError(None, 10000, err)

def add_series_rule(params):
    try:
        _name = params.get('name')
        _lengths = (int(_item) for _item in params.get('length').split(','))
        _count=0
        for _length in _lengths:
            _rule, _created=SeriesRule.objects.get_or_create(name = _name, length = _length)
            if _created:
                _rule.save()
                _count+=1
                _values=calc_current(_name, _length)
                _limit_date=datetime.date.today()-datetime.timedelta(hours=24*(_length-1))
                SeriesCurrent(name=_name,
                              length=_length,
                              day_trimmed=_limit_date,
                              values=_values
                              ).save()

        return _count
    except Exception, err:
        raise ApiError(None, 10000, err)

def del_series_rule(params):
    try:
        _name = params.get('name')
        _lengths = (int(_item) for _item in params.get('length').split(','))
        _count=0
        for _length in _lengths:
            try:
                SeriesRule.objects.get(name = _name, length = _length).delete()
                _count+=1
            except ObjectDoesNotExist, err:
                pass
            try:
                SeriesCurrent.objects.get(name=_name, 
                                        length=_length
                                        ).delete()    
            except ObjectDoesNotExist, err:
                pass
        return _count
    except Exception, err:
        raise ApiError(None, 10000, err)
    
#===============SERIES KEYS=============#

def get_series_keys(params):
    try:
        _keys=set(SeriesToday.objects.all().values_list("name", flat=True).distinct())
        _keys=_keys.union(SeriesHistory.objects.all().values_list("name", flat=True).distinct())
        return list(_keys)
    except Exception, err:
       raise ApiError(None, 10000, err)

