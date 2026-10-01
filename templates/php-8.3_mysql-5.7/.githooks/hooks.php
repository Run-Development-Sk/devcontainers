<?php
/**
 * Git hooks of the project. The hook scripts in this folder (except pre-commit,
 * which runs .pre-commit-config.yaml) are thin wrappers which call this script
 * with the hook name followed by the hook arguments.
 * The folder is activated by core.hooksPath in default.gitconfig.
 *
 * After each checkout, merge and merge commit (a merge finished by `git commit`
 * after resolving conflicts) it:
 * - lists changed files of bundled React subprojects to warn user that they
 *   must be rebuilt manually by `npm run build`,
 * - recompiles .less files by `gulp compile-less --recompile --quiet`.
 *
 * Rebase (incl. `git pull --rebase`) is covered by post-checkout hook which
 * git launches when rebase checks out the new base.
 */
if (PHP_SAPI !== 'cli') {
    exit;
}

// hash of the empty tree, used as the start of the diff if there is no previous HEAD
define('_EMPTY_TREE', '4b825dc642cb6eb9a060e54bf8d69288fbee4904');
define('_NULL_REV', '0000000000000000000000000000000000000000');

$hook = isset($argv[1]) ? $argv[1] : null;
if ($hook === 'post-checkout') {
    // ignore file checkouts and checkouts which do not change HEAD
    if (
        $argv[4] !== '1'
        || $argv[2] === $argv[3]
    ) {
        exit;
    }
    $startRev = $argv[2] === _NULL_REV ? _EMPTY_TREE : $argv[2];
    $endRev = $argv[3];
    $isMerge = false;
}
elseif ($hook === 'post-merge') {
    $startRev = 'ORIG_HEAD';
    $endRev = 'HEAD';
    $isMerge = true;
}
elseif ($hook === 'post-commit') {
    // only merge commits are considered
    exec('git rev-parse --quiet --verify HEAD^2', $output, $exitCode);
    if ($exitCode !== 0) {
        exit;
    }
    $startRev = 'HEAD^1';
    $endRev = 'HEAD';
    $isMerge = true;
}
else {
    echo "Unknown git hook '{$hook}'\n";
    exit;
}

chdir(dirname(__DIR__));

echo "\nChecking for changes in React projects files from {$startRev} to {$endRev}.\n";
$files = array();
exec(
    'git diff --name-only ' . escapeshellarg($startRev) . ' ' . escapeshellarg($endRev),
    $files,
    $exitCode
);
// find bundled sub-projects to warn user that they must be build manually using `npm run build`
$bundledSubProjectsFiles = array();
foreach ($files as $file) {
    if (preg_match('#/react/#', $file)) {
        $bundledSubProjectsFiles[] = $file;
    }
}
if ($exitCode !== 0) {
    echo "\e[01;37mATTENTION:\e[00m Changed files cannot be resolved, check React projects files manually.\n";
}
elseif ($bundledSubProjectsFiles) {
    echo "\e[01;37mFollowing changes in React projects files has been found:\e[00m\n";
    foreach ($bundledSubProjectsFiles as $file) {
        if (!file_exists($file)) {
            echo "\e[01;37mATTENTION:\e[00m File $file does not exist in actual working directory!\n";
            continue;
        }
        echo $file . "\n";
    }
    if ($isMerge) {
        echo "\e[01;37mConsider to rebuild manually concerned React projects by `npm run build` and to commit the rebuilt bundles.\e[00m\n";
    }
    else {
        echo "\e[01;37mConsider to rebuild manually concerned React projects by `npm run build`.\e[00m\n";
    }
}
else {
    echo "\e[01;37mNo changes in React projects files has been found\e[00m\n";
}
echo "\n";

// gulp requires node 17 - if nvm is installed then `nvm exec` launches gulp
// under node 17 in a subprocess, so the node version used in user's shell stays untouched
$gulpCommand = 'gulp compile-less --recompile --quiet';
$nvmDir = getenv('NVM_DIR') ?: getenv('HOME') . '/.nvm';
if (is_readable($nvmDir . '/nvm.sh')) {
    $gulpCommand = 'bash -c ' . escapeshellarg(
        '. ' . escapeshellarg($nvmDir . '/nvm.sh') . ' && nvm exec --silent 17 ' . $gulpCommand
    );
}
passthru($gulpCommand, $exitCode);
if ($exitCode !== 0) {
    echo "\e[01;37mATTENTION:\e[00m Compilation of .less files by gulp has failed (are node 17 and 'gulp' command available?).\n";
}
