
version=$(hatch version | sed -rne "s:([0-9]*)\.([0-9]*)\..*:\1.\2:p")

git fetch origin gh-pages
hatch run docs:mike deploy -u --push ${version} latest
