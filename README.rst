A forked version of the Jinja 1 module from http://jinja.pocoo.org

Changes include:

* Removal of djangosupport.configure() (you now simply import jinja.contrib.djangosupport)
* Added jinja.contrib.djangosupport.handler404
* Added jinja.contrib.djangosupport.handler500
* Added jinja.contrib.djangosupport.direct_to_template