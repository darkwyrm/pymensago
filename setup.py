from setuptools import setup, find_packages

setup(
	name='pyanselus',
	version='0.1',
	description='library for writing Anselus clients',
	url='https://github.com/darkwyrm/pyanselus',
	author='Jon Yoder',
	author_email='jsyoder@mailfence.com',
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
		# 'blake3>=0.1.7',
		'PyNaCl>=1.3.0',
		'jsonschema>=3.2.0'
	]
)
