const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ALGORITHM = 'aes-256-cbc';
const SALT_SIZE = 16;
const IV_SIZE = 16;
const KEY_LEN = 32; // 256 bits

function showUsage() {
    console.log('Usage:');
    console.log('  node secure_file.js encrypt <file> <password>');
    console.log('  node secure_file.js decrypt <file> <password>');
}

async function scrypt(password, salt) {
    return new Promise((resolve, reject) => {
        crypto.scrypt(password, salt, KEY_LEN, (err, key) => {
            if (err) reject(err);
            else resolve(key);
        });
    });
}

async function encrypt(filePath, password) {
    if (fs.lstatSync(filePath).isDirectory()) {
        const files = fs.readdirSync(filePath);
        for (const file of files) {
            const fullPath = path.join(filePath, file);
            // Ignore .git, node_modules, and this script
            if (file === '.git' || file === 'node_modules' || file === 'secure_file.js' || file.endsWith('.enc')) continue;
            await encrypt(fullPath, password);
        }
        return;
    }

    const data = fs.readFileSync(filePath);
    const salt = crypto.randomBytes(SALT_SIZE);
    const iv = crypto.randomBytes(IV_SIZE);

    const key = await scrypt(password, salt);
    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

    const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);

    // Format: SALT (16) + IV (16) + ENCRYPTED_DATA
    const output = Buffer.concat([salt, iv, encrypted]);

    const outputPath = filePath + '.enc';
    fs.writeFileSync(outputPath, output);
    console.log(`Encrypted: ${filePath}`);
    // Optional: fs.unlinkSync(filePath); // We will do this manually or after confirmation
}

async function decrypt(filePath, password) {
    if (fs.lstatSync(filePath).isDirectory()) {
        const files = fs.readdirSync(filePath);
        for (const file of files) {
            const fullPath = path.join(filePath, file);
            await decrypt(fullPath, password);
        }
        return;
    }

    if (!filePath.endsWith('.enc')) return;

    const data = fs.readFileSync(filePath);

    const salt = data.slice(0, SALT_SIZE);
    const iv = data.slice(SALT_SIZE, SALT_SIZE + IV_SIZE);
    const encryptedData = data.slice(SALT_SIZE + IV_SIZE);

    const key = await scrypt(password, salt);
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);

    try {
        const decrypted = Buffer.concat([decipher.update(encryptedData), decipher.final()]);

        let outputPath = filePath.slice(0, -4);
        fs.writeFileSync(outputPath, decrypted);
        console.log(`Decrypted: ${outputPath}`);
        // fs.unlinkSync(filePath); // Keep .enc for now
    } catch (e) {
        console.error(`Failed to decrypt ${filePath}: Incorrect password.`);
    }
}

const [action, file, password] = process.argv.slice(2);

if (!action || !file || !password) {
    showUsage();
    process.exit(1);
}

if (action === 'encrypt') {
    encrypt(file, password).catch(console.error);
} else if (action === 'decrypt') {
    decrypt(file, password).catch(console.error);
} else {
    showUsage();
}
