import setuptools

setuptools.setup(
    name="mindx_elastic",
    version="0.0.1",
    platforms=['linux', ],
    description="Ascend MindX Elastic is a new library for fault tolerance training.",
    packages=setuptools.find_packages(),
    python_requires='>=3.7',
    install_requires=["mindspore-ascend >= 1.5.0"]
)