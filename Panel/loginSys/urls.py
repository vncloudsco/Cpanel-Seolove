from django.urls import path
from . import views
from phpManager import views as view_php_manager
# SET THE NAMESPACE!
app_name = 'loginSys'

# Be careful setting the name to just /login use userlogin instead!
urlpatterns=[
    path('',views.index,name='index'),
    path('login/',views.login,name='login'),
    path('authi/',views.authi,name='authi'),
    path('logout/',views.logout,name='logout'),
    path('load_chart/',views.load_chart,name='load_chart'),
    path('settings/changePassword',views.changePassword,name='changePassword'),
    path('cPanel/settings/updateScript', view_php_manager.updateScript, name='updateScript'),
    path('cPanel/settings/updateVersion', view_php_manager.updateVersion, name='updateVersion'),
]