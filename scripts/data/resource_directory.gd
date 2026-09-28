extends RefCounted
class_name ResourceDirectory

## Lists the loadable .tres resources in a res:// folder, in a way that
## works both in the editor and in exported builds.
##
## Exported projects convert text resources to binary by default, and a
## folder listing then shows "name.tres.remap" instead of "name.tres".
## load() still resolves the original "name.tres" path through the remap,
## so the fix is simply to recognise the ".remap" form and strip it.
## Without this, a folder scan that only accepts ".tres" finds nothing on
## Android. Results are sorted so load order never depends on the
## filesystem.

const REMAP_SUFFIX := ".remap"

static func list_tres_paths(dir_path: String) -> Array[String]:
	var paths: Array[String] = []
	var dir := DirAccess.open(dir_path)
	if dir == null:
		push_warning("ResourceDirectory: could not open %s" % dir_path)
		return paths
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir():
			var resource_name := file_name.trim_suffix(REMAP_SUFFIX)
			if resource_name.ends_with(".tres"):
				var full_path := dir_path.path_join(resource_name)
				if not paths.has(full_path):
					paths.append(full_path)
		file_name = dir.get_next()
	dir.list_dir_end()
	paths.sort()
	return paths
