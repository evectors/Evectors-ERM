from django.db import connection

def require_lock(*tables):
    def _lock(func):
        def _do_lock(*args,**kws):
            #lock tables
            cursor = connection.cursor()
            lock_query="LOCK TABLES %s WRITE" %' WRITE, '.join(tables)
            cursor.execute(lock_query)
            
            try:
                result = func(*args,**kws)
            except Exception,e:
                raise Exception(e)
            else:
                return result
            finally:
                #unlock tables
                cursor.execute("UNLOCK TABLES")
                if cursor:
                    cursor.close()
        return _do_lock
    return _lock
