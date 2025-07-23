`external_file()` is a lower-level solution than `external()`.
It accepts one argument, which is the path to the file where your external object should be stored.
It will only *create* or *fix* the given files and will never *trim* unused files.


You can use it to generate files in your project.

``` python
def test_generate_doc():
    assert generate_features_doc() == external_file("all_features.md")
```

inline-snapshot checks whether your documentation is up to date and displays a diff that you can approve if necessary.

Another use case is to check if some files in your project are correct by reading the file, transforming it, and comparing it with the current version.
The transformation (`eval_code_blocks()` in the example) of the text should produce the same result if everything is correct.
The test will fail if the transformation results in different output, and inline-snapshot will show you the diff, as it does for other external comparisons.

``` python
def test_files():
    for file in root.rglob("*.md", format=".txt"):
        current_text = file.read_text()

        # eval_code_blocks is a custom function that could run your examples in a project-specific way and store the output in the documentation.
        # It is up to you to implement such functions for your specific use case.
        correct_text = eval_code_blocks(current_text)

        assert correct_text == external_file(file)
```

::: inline_snapshot
    options:
      heading_level: 3
      members: [external_file]
      show_root_heading: false
      show_bases: false
      show_source: false
