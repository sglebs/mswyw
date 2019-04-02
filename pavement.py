from paver.setuputils import setup
from setuptools import find_packages
from utilities import VERSION
setup(
    name='mswyw',
    description='Microservise: Worth Your Weight?',
    packages=find_packages(),
    version=VERSION,
    url='https://github.com/sglebs/mswyw',
    author='Marcio Marchini',
    author_email='marcio@betterdeveloper.net',
    install_requires=[
        'docopt==0.6.2',
        'requests==2.10.0',
        'requests-file'
    ],
    entry_points={
        'console_scripts': [
            'mswyw = utilities.mswyw:main'
        ],
    }
)
