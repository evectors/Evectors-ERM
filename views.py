from django.http import HttpResponseRedirect

def root_redirect( request ):
   return HttpResponseRedirect( "/admin/")
