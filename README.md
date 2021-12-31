# pymensago

A Python module implementing various components and services to enable creation of [Mensago](https://mensago.org) clients released under the MIT license.

## Description

pymensago originally started as a quickie test client to interact with server code and guide client-side spec development. As it developed, though, it has taken on a shape of its own. It has been written primarily in mind for development of the upcoming CLI Mensago client [Smilodon](https://github.com/darkwyrm/smilodon) and some yet-to-be-released utilities, but it is implemented in a generic way that it can be used for any Mensago client development.

## Status

The library is in the early stages, but now that the reference server implementation, [mensagod](https://github.com/mensago/mensagod), has seen significant development, it is seeing much more progress. 

## Building

Setup is a matter of checking out the repository, setting up your virtual environment, and `pip install -r requirements.txt`, and then `pip install .`. Once it is more stable, it will be available from PyPi.

