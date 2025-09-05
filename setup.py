from distutils.core import setup

setup(
    name="mpgdb",
    description="GDB plugin library for debugging MicroPython.",
    author="Anson Mansfield",
    author_email="amansfield@mantaro.com",
    packages=["mpgdb"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Debuggers",
    ],
)