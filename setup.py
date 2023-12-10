from distutils.core import setup
from setuptools import find_packages

setup(
    name='pyrtmp',
    packages=find_packages(),
    version='0.3.0',
    license='MIT',
    description='PyRTMP: Pure Python RTMP server',
    author='Eittipat.K',
    author_email='iammop@gmail.com',
    url='https://github.com/Eittipat/pyrtmp.git',
    download_url='https://github.com/Eittipat/pyrtmp/releases/tag/v0.3.0',
    keywords=['RTMP', 'RTMPT', 'asyncio'],
    python_requires='>=3.10',
    install_requires=[
        'bitstring>=4'
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
    ],
)
