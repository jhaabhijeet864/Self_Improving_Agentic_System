#!/usr/bin/env node

/**
 * Jarvis-OS Node.js CLI Entrypoint
 * Cross-Platform Launcher that bootstraps the native Python environment.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

// Wrap imports in try/catch in case skipped npm install
let chalk, ora;
try {
  chalk = require('chalk');
  ora = require('ora');
} catch (e) {
  console.log("Installing CLI dependencies...");
  execSync('npm install chalk@4.1.2 ora@5.4.1', { stdio: 'ignore' });
  chalk = require('chalk');
  ora = require('ora');
}

const venvDir = path.join(__dirname, '.jarvis-env');
const isWin = process.platform === "win32";
const pythonCmd = isWin ? path.join(venvDir, 'Scripts', 'python.exe') : path.join(venvDir, 'bin', 'python');
const pipCmd = isWin ? path.join(venvDir, 'Scripts', 'pip.exe') : path.join(venvDir, 'bin', 'pip');

async function checkPythonVersion() {
  try {
    const rawOutput = execSync('python --version', { encoding: 'utf-8' });
    const versionMatch = rawOutput.match(/Python (\d+)\.(\d+)/);
    if (versionMatch) {
      const major = parseInt(versionMatch[1]);
      const minor = parseInt(versionMatch[2]);
      if (major >= 3 && minor >= 10) return true;
    }
  } catch (e) { }
  return false;
}

function setupEnvironment() {
  return new Promise((resolve, reject) => {
    const spinner = ora('Initializing Jarvis-OS Engine ecosystem...').start();

    // Check if python available
    if (!checkPythonVersion()) {
      spinner.fail(chalk.red('Python 3.10+ is required but was not found in PATH.'));
      process.exit(1);
    }

    if (!fs.existsSync(venvDir)) {
      spinner.text = 'Creating isolated Python environment (.jarvis-env)...';
      try {
        execSync(`python -m venv ${venvDir}`, { stdio: 'ignore' });
      } catch (err) {
         spinner.fail(chalk.red('Failed to create Python virtual environment.'));
         process.exit(1);
      }
    }

    spinner.text = 'Verifying Jarvis dependencies...';
    try {
      execSync(`${pipCmd} install -r requirements.txt`, { cwd: __dirname, stdio: 'ignore' });
      spinner.succeed(chalk.green('Jarvis-OS ecosystem is primed and ready.'));
      resolve();
    } catch (err) {
      spinner.fail(chalk.red('Failed to install Python requirements.'));
      process.exit(1);
    }
  });
}

async function startJarvisDaemon() {
  console.log(chalk.cyan.bold('\n🚀 Booting Jarvis-OS Core Daemon...'));
  
  // Decide which file to run
  const backendScript = "win32_daemon.py"; 
  
  const jarvisProc = spawn(pythonCmd, [path.join(__dirname, backendScript)], {
    cwd: __dirname,
    env: { ...process.env, PYTHONUNBUFFERED: "1" } // Force flush stdout
  });

  jarvisProc.stdout.on('data', (data) => {
    const lines = data.toString().split('\n');
    lines.forEach(line => {
      if (!line.trim()) return;
      if (line.includes('INFO')) console.log(`${chalk.blue('ℹ')} ${chalk.gray(line.trim())}`);
      else if (line.includes('ERROR')) console.log(`${chalk.red('✖')} ${chalk.redBright(line.trim())}`);
      else if (line.includes('WARNING')) console.log(`${chalk.yellow('⚠')} ${chalk.yellow(line.trim())}`);
      else console.log(`${chalk.white('›')} ${line.trim()}`);
    });
  });

  jarvisProc.stderr.on('data', (data) => {
      console.error(chalk.red(`[Jarvis-Core Error]: ${data.toString()}`));
  });

  jarvisProc.on('close', (code) => {
    console.log(chalk.red(`\nJarvis-OS daemon exited with code ${code}`));
    process.exit(code);
  });

  console.log(chalk.green('──────────────────────────────────────────────────'));
  console.log(chalk.green.bold('✔ Jarvis Dashboard: ') + chalk.white.underline('http://localhost:8000'));
  console.log(chalk.green.bold('✔ Swara IPC Bridge: ') + chalk.white('\\\\.\\pipe\\jarvis_ipc'));
  console.log(chalk.green('──────────────────────────────────────────────────\n'));
  
  // Keep alive
  readline.emitKeypressEvents(process.stdin);
  if(process.stdin.isTTY) process.stdin.setRawMode(true);
  
  process.stdin.on('keypress', (str, key) => {
    if (key.ctrl && key.name === 'c') {
      console.log(chalk.yellow('\nShutting down Jarvis-OS...'));
      jarvisProc.kill('SIGINT');
      process.exit();
    }
  });
}

(async () => {
  await setupEnvironment();
  await startJarvisDaemon();
})();
