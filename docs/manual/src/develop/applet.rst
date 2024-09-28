.. _applet:

Applets
=======

.. attention::

    We do not yet have documentation for developing applets or a stable API, so for now every applet must be loaded from within the main ``glasgow`` package.


You can add a new applet by defining its entry point in `pyproject.toml`.
An example applet is provided in `examples/boilerplate.py`.

Tests can be run with `glasgow test <applet name>`.
