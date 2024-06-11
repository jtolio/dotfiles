#!/usr/bin/env python

#pylint: disable-all
#pylint: skip-file

import sys
import hashlib
import argparse
from collections import Counter
from functools import partial
from subprocess import check_output
from warnings import warn


def git_ref_field(git_dir, ref, field, _cache={}):
  key = (git_dir, ref, field)
  if key in _cache:
    return _cache[key]
  result = check_output(
      ["git", "log", "-1", "--format=%s" % field, ref], cwd=git_dir).decode("utf8")
  _cache[key] = result
  return result


def git_resolve(git_dir, ref):
  return git_ref_field(git_dir, ref, "%H").strip()


def git_tree(git_dir, ref):
  return git_ref_field(git_dir, ref, "%T").strip()


def git_parents(git_dir, ref):
  return git_ref_field(git_dir, ref, "%P").strip().split()


def git_subject(git_dir, ref):
  return git_ref_field(git_dir, ref, "%s").strip()


def git_change_id(git_dir, ref):
  change_id = None
  for line in git_ref_field(git_dir, ref, "%b").strip().split("\n"):
    line = line.strip()
    if not line:
      continue
    if line.startswith("Change-Id: "):
      if change_id is not None:
        warn("Commit %s has two change ids, using metahash" % ref[:8])
        change_id = git_metahash(git_dir, ref)
      else:
        _, change_id = line.split()
  if change_id is None:
    warn("Commit %s has no change id, using metahash" % ref[:8])
    change_id = git_metahash(git_dir, ref)
  return change_id


def git_metahash(git_dir, ref):
  meta = git_ref_field(git_dir, ref, "%b:%an:%ae:%at:%s")
  return hashlib.sha256(meta.encode("utf8")).hexdigest()


def shortest_path(git_dir, child, tree_hash):
  child_tree = git_tree(git_dir, child)
  if child_tree == tree_hash: return []
  best_path = None
  for parent in git_parents(git_dir, child):
    path = shortest_path(git_dir, parent, tree_hash)
    if path is None:
      continue
    if best_path is None or len(best_path) > len(path):
      best_path = path
  if best_path is None:
    return None
  return [child] + best_path


def find_treesame_ring(git_dir, *refs):
  tree_hash_sets = []
  queues = []
  for ref in refs:
    tree_hashes = set()
    tree_hash_sets.append(tree_hashes)
    queues.append({"tree_hashes": tree_hashes, "queue": [ref]})
  while queues:
    queue = queues.pop(0)
    ref = queue["queue"].pop(0)
    tree_hash = git_tree(git_dir, ref)
    queue["tree_hashes"].add(tree_hash)
    candidate = True
    for tree_hashes in tree_hash_sets:
      if tree_hash not in tree_hashes:
        candidate = False
    if candidate:
      return tree_hash
    queue["queue"].extend(git_parents(git_dir, ref))
    if queue["queue"]:
      queues.append(queue)
  return None


def changelog(git_dir, from_ref, to_ref):
  tree_hash = find_treesame_ring(git_dir, from_ref, to_ref)
  from_refs = shortest_path(git_dir, from_ref, tree_hash)
  to_refs = shortest_path(git_dir, to_ref, tree_hash)
  to_refs.reverse()
  return from_refs, to_refs


def print_filtered(git_dir, from_ref, to_ref, filter_cherry_picks=None,
                   predicate=None):
  from_refs, to_refs = changelog(git_dir, from_ref, to_ref)
  if predicate:
    from_refs = filter(predicate, from_refs)
    to_refs = filter(predicate, to_refs)

  def info(ref):
    change_id = None
    if filter_cherry_picks is not None:
      change_id = filter_cherry_picks(git_dir, ref)
    return (ref, git_subject(git_dir, ref), change_id)

  from_refs = list(map(info, from_refs))
  to_refs = list(map(info, to_refs))
  both = set()
  if filter_cherry_picks is not None:
    from_change_ids = Counter([change_id for _, _, change_id in from_refs])
    to_change_ids = Counter([change_id for _, _, change_id in to_refs])
    for change_id, counter in list(from_change_ids.items()) + list(to_change_ids.items()):
      if counter > 1:
        warn("Change id %s applied on branch twice" % change_id)
    both = set(from_change_ids.keys()) & set(to_change_ids.keys())

  def merge_msg(ref):
    parents = git_parents(git_dir, ref)
    if len(parents) <= 1:
      return ""
    return "[M]"

  for ref, subject, change_id in from_refs:
    if change_id not in both:
      print("[- %s]%s %s" % (ref[:8], merge_msg(ref), subject))
  for ref, subject, change_id in to_refs:
    if change_id not in both:
      print("[+ %s]%s %s" % (ref[:8], merge_msg(ref), subject))


def prefix_changed(git_dir, prefix, ref):
  files = check_output(["git", "diff", "%s^" % ref, ref, "--name-only"]).decode("utf8")
  files = files.strip().split()
  for fname in files:
    if fname.startswith(prefix):
      return True
  return False


def main():
  p = argparse.ArgumentParser(description=(
      "a better git changelog. attempts to show the minimum path along the "
      "graph of applied changes to go from one tree state to another."))
  p.add_argument("from_ref", help="the ref to show the path from")
  p.add_argument("to_ref", help="the ref to show the path to")
  p.add_argument("--cherry-picks", action="store_true", help=(
      "if set, does not filter commits by assuming the same change id on "
      "two branches is just a cherry pick"))
  p.add_argument("--prefix", help=(
      "if set, only considers commits that change paths with the given "
      "prefix"))
  p.add_argument("--gerrit", action="store_true", help=(
      "if set, filters commits via gerrit change ids. mutually exclusive "
      "with --cherry-picks"))
  p.add_argument("--git-dir", default=".", help=(
      "if set, the path to the git directory to consider. if unset, uses "
      "the current directory"))
  args = p.parse_args()

  from_ref = git_resolve(args.git_dir, args.from_ref)
  to_ref = git_resolve(args.git_dir, args.to_ref)
  predicate = None
  if args.prefix:
    predicate = partial(prefix_changed, args.git_dir, args.prefix)
  filter_cherry_picks = None
  if not args.cherry_picks:
    if args.gerrit:
      filter_cherry_picks = git_change_id
    else:
      filter_cherry_picks = git_metahash

  print_filtered(
      args.git_dir, from_ref, to_ref,
      filter_cherry_picks=filter_cherry_picks, predicate=predicate)


if __name__ == "__main__":
  main()
