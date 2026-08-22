#!/bin/sh
set -eu

mkdir -p ~/.ssh
chmod 700 ~/.ssh

KEY="$HOME/.ssh/id_ed25519_github"
if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -C "beget-nl-vps github" -f "$KEY" -N ""
  echo "Created new key: $KEY"
else
  echo "Key already exists: $KEY"
fi

chmod 600 "$KEY"
chmod 644 "${KEY}.pub"

cat > "$HOME/.ssh/config" <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
EOF
chmod 600 "$HOME/.ssh/config"

echo
echo "Add this public key to GitHub (Settings -> SSH and GPG keys):"
echo
cat "${KEY}.pub"
