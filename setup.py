from distutils.core import setup
from setuptools import find_packages

setup(
    name='pyrtmp',
    packages=find_packages(),
    version='0.1.4',
    license='MIT',
    description='Pure python RTMP server',
    author='Eittipat.K',
    author_email='iammop@gmail.com',
    url='https://github.com/Eittipat/pyrtmp.git',
    download_url='https://github.com/Eittipat/pyrtmp/releases/tag/v0.1.4',
    keywords=['RTMP', 'RTMPT', 'asyncio'],
    python_requires='>=3',
    install_requires=[
        'aiounittest>=1.4.0',
        'bitstring>=3.1.7',
        'Quart>=0.15.1',
        'psutil>=5.8.0',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
