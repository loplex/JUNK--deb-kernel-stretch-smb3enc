#!/usr/bin/python3

import errno, io, os, os.path, re, shutil, subprocess, sys, tempfile

def main(source, base, branch):
    patch_dir = 'debian/patches'
    sl_patch_dir = 'features/all/securelevel'
    series_name = 'series'
    old_series = set()
    new_series = set()

    with open(os.path.join(patch_dir, series_name), 'r') as series_fh, \
         open(os.path.join(patch_dir, series_name + '.new'), 'w') \
         as new_series_fh:
        before = True

        # Add Origin to all patch headers.
        def add_patch(name, source_patch, origin):
            name = os.path.join(sl_patch_dir, name)
            path = os.path.join(patch_dir, name)
            try:
                os.unlink(path)
            except OSError as e:
                if e.errno != errno.ENOENT:
                    raise
            with open(path, 'w') as patch:
                in_header = True
                for line in source_patch:
                    if in_header and re.match(r'^(\n|[^\w\s]|Index:)', line):
                        patch.write('Origin: %s\n' % origin)
                        if line != '\n':
                            patch.write('\n')
                        in_header = False
                    patch.write(line)
            new_series_fh.write(name + '\n')
            new_series.add(name)

        for line in series_fh:
            name = line.strip()
            if not name.startswith(sl_patch_dir + '/'):
                new_series_fh.write(line)
            else:
                old_series.add(name)
                if before:
                    args = ['git', 'format-patch', '%s..%s' % (base, branch)]
                    env = os.environ.copy()
                    env['GIT_DIR'] = os.path.join(source, '.git')
                    child = subprocess.Popen(args,
                                             cwd=os.path.join(patch_dir, sl_patch_dir),
                                             env=env, stdout=subprocess.PIPE)
                    with io.open(child.stdout.fileno(), encoding='utf-8') as pipe:
                        for line in pipe:
                            name = line.strip('\n')
                            with open(os.path.join(patch_dir, sl_patch_dir, name)) as \
                                    source_patch:
                                patch_from = source_patch.readline()
                                match = re.match(r'From ([0-9a-f]{40}) ', patch_from)
                                assert match
                                origin = 'https://git.kernel.org/cgit/linux/kernel/git/jforbes/linux.git/commit?id=%s' % match.group(1)
                                add_patch(name, source_patch, origin)
                    before = False

    os.rename(os.path.join(patch_dir, series_name + '.new'),
              os.path.join(patch_dir, series_name))

    for name in new_series:
        if name in old_series:
            old_series.remove(name)
        else:
            print('Added patch', os.path.join(patch_dir, name))

    for name in old_series:
        print('Obsoleted patch', os.path.join(patch_dir, name))

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('Usage: %s REPO BASE BRANCH' % sys.argv[0], file=sys.stderr)
        print('REPO is a git repo containing securelevel patches between BASE and BRANCH.', file=sys.stderr)
        sys.exit(2)
    main(*sys.argv[1:])
