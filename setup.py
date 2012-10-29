from setuptools import setup, find_packages
import sys, os

version = '1.0htug4'
shortdesc ="LDAP Plugin for Zope2 PluggableAuthService (users and groups)"
longdesc = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'TODO.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'HISTORY.rst')).read()
longdesc += open(os.path.join(os.path.dirname(__file__), 'LICENSE.rst')).read()

setup(name='pas.plugins.ldap',
      version=version,
      description=shortdesc,
      long_description=longdesc,
      classifiers=[
            'Environment :: Web Environment',
            'Framework :: Zope2',
            'Operating System :: OS Independent',
            'Programming Language :: Python',           
      ], # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      keywords='zope2 pas plone ldap',
      author='BlueDynamics Alliance',
      author_email='dev@bluedynamics.com',
      url='https://github.com/collective/pas.plugins.ldap',
      license='BSD like',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['pas', 'pas.plugins'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools', 
          'Products.PlonePAS',
          'five.globalrequest',
          'node.ext.ldap',
          'yafowil.plone>=1.3',         
          'yafowil.widget.dict',
          'yafowil.widget.array',
      ],
      extras_require={
          'test': [
              'interlude',
              'zope.configuration',
              'zope.testing',
              'plone.testing',
          ],
          'plone': [
              'Plone',
          ]
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,     
      )
