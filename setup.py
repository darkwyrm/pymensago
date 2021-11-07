from setuptools import setup, find_packages

setup(
	name='pymensago',
	version='0.1',
	description='library for writing Mensago clients',
	url='https://github.com/darkwyrm/pymensago',
	author='Jon Yoder',
	author_email='jon@yoder.cloud',
	license='MIT',
	packages=find_packages(),
	classifiers=[
		"Development Status :: 2 - Pre-Alpha",
		"Intended Audience :: Developers",
		"Topic :: Communications",
		"Programming Language :: Python :: 3.5",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.5',
	install_requires=[
		'blake3>=0.1.7',
		'distro>=1.5.0',
		'PyNaCl>=1.3.0',
		'jsonschema>=3.2.0',
		'pillow>=8.2.0',
		'pycryptostring>=1.0.0',
		'retval>=1.0.0',
		'toml>=0.10.2',
		'dnspython>=2.1.0',
		'pycryptodome>=3.11.0'
	]
)
