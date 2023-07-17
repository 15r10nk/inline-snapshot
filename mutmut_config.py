def pre_mutation(context):
    line = context.current_source_line.strip()
    if line.strip().startswith(("assert False", "@overload", "= TypeVar")):
        context.skip = True
