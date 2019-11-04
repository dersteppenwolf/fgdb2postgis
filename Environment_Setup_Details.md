# A Guide To Translating FGDB Schema To PG

## fgdb2postgis Fork Source
[fgdb2postgis](https://github.com/dersteppenwolf/fgdb2postgis)
Note that this project has been forked to The Lorrnel Group from the latest maintained version.

### Set Paths
Start Button > Right Click Properties >Advanced system settings > Advanced Tab > Environemnt Variables > user varibales >
Look for a variable called path, if if is there edit, if not new:

Variable Name: path
Variable Value: (separated by ; if on windows 7, new entry on windows 10)
C:\Python27\ArcGIS10.3\Scripts
C:\Python27\ArcGIS10.3

Open comand promt (cmd)

```python```
Should return python version

```python -m pip help install```
Should return pip help

pip:
[https://pip.readthedocs.io/en/latest/installing/](https://pip.readthedocs.io/en/latest/installing/)

If you have numpy and you can not upgrade or uninstall it with pip it was installed by another method.  Delete it's references from:
C:\Python27\ArcGIS10.3\Lib\site-packages

From the comand prompt:
```
python -m pip uninstall numpy
python -m pip install numpy==1.16.5 
```
Successfully installed numpy-1.16.5
```
python -m pip install pyyaml
python -m pip install psycopg2
python -m pip install archook
```
Successfully installed pyyaml-5.1.2
Successfully installed psycopg2-2.8.4
Successfully installed archook-1.2.0

To make sure you ahve the latest version download [fgdb2postgis](https://github.com/dersteppenwolf/fgdb2postgis) and install from file:

```python -m pip install C:\Temp\fgdb2postgis-master```

This will install the package at:
C:\Python27\ArcGIS10.3\Lib\site-packages

