__author__ = 'lobocv'

from distutils.core import setup
from crashreporter import __version__
from os.path import join

setup(
    name='crashreporter-hq',
    packages=['crashreporter'],  # this must be the same as the name above
    package_dir={'crashreporter': 'crashreporter'},
    package_data={'crashreporter': [join('crashreporter_hq', 'templates', '*.html')]},
    version=__version__,
    description='Track and send crash reports by email or upload them to a webserver.',
    author='Calvin Lobo',
    author_email='calvinvlobo@gmail.com',
    license='MIT',
    url='https://github.com/lobocv/crashreporter',
    download_url='https://github.com/lobocv/crashreporter/tarball/%s' % __version__,
    keywords=['crash', 'reporting', 'testing', 'debugging', 'bugs'],
    classifiers=[],
    install_requires=['jinja2', 'requests']
)
