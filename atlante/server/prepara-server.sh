#!/bin/sh
# Copyright (c) 2026 Zeta3. Parte di Atlante, copia modificata di Plane.
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Puts a new Ubuntu 24.04 server in order for the test of Atlante (zeta3-progetti, docs/collaudo-0.3.md,
# section 1; docs/regole/sicurezza.md, level 2). Run as root, in two steps, so nobody is locked out:
#
#   sh prepara-server.sh utente   # user "atlante" with root's SSH keys, firewall, automatic updates, Docker
#   (from the Mac: ssh atlante@<server> sudo true  must work before the second step)
#   sh prepara-server.sh chiudi   # SSH only with keys, only for "atlante": no root, no passwords
#
# Run again, it changes nothing that is already in order.

set -eu
export DEBIAN_FRONTEND=noninteractive
UTENTE=atlante
# Wait if the provider's own updates are running; keep the configuration files already there, ask nothing.
APT="apt-get -y -q -o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold"

[ "$(id -u)" -eq 0 ] || { echo "Va lanciato come root."; exit 1; }
. /etc/os-release
[ "$ID" = ubuntu ] || { echo "Pensato per Ubuntu 24.04: qui c'è $PRETTY_NAME."; exit 1; }

utente() {
	# The technical access: a personal key, no password at all (sudo without password, only with the key).
	id "$UTENTE" >/dev/null 2>&1 || adduser --disabled-password --gecos "Atlante" "$UTENTE"
	passwd -l "$UTENTE" >/dev/null
	install -d -m 700 -o "$UTENTE" -g "$UTENTE" "/home/$UTENTE/.ssh"
	[ -s /root/.ssh/authorized_keys ] || { echo "Root non ha chiavi SSH: aggiungi la chiave pubblica e riprova."; exit 1; }
	install -m 600 -o "$UTENTE" -g "$UTENTE" /root/.ssh/authorized_keys "/home/$UTENTE/.ssh/authorized_keys"
	echo "$UTENTE ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-atlante
	chmod 440 /etc/sudoers.d/90-atlante
	visudo -cf /etc/sudoers.d/90-atlante >/dev/null

	$APT update
	$APT upgrade
	$APT install ca-certificates curl openssl ufw unattended-upgrades

	# Automatic system updates every night; a restart, if one is needed, at 4 in the morning.
	cat > /etc/apt/apt.conf.d/20auto-upgrades <<-EOF
		APT::Periodic::Update-Package-Lists "1";
		APT::Periodic::Unattended-Upgrade "1";
	EOF
	cat > /etc/apt/apt.conf.d/52atlante-upgrades <<-EOF
		Unattended-Upgrade::Automatic-Reboot "true";
		Unattended-Upgrade::Automatic-Reboot-Time "04:00";
	EOF
	systemctl enable --now unattended-upgrades >/dev/null

	# From outside only SSH and the site. Docker publishes only 80 and 443 (docker-compose.collaudo.yml).
	ufw default deny incoming >/dev/null
	ufw default allow outgoing >/dev/null
	ufw allow 22/tcp >/dev/null
	ufw allow 80/tcp >/dev/null
	ufw allow 443/tcp >/dev/null
	ufw --force enable >/dev/null

	# Docker from Docker's own repository, with logs that do not fill the disk.
	if ! command -v docker >/dev/null 2>&1; then
		install -m 0755 -d /etc/apt/keyrings
		curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
		echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" \
			> /etc/apt/sources.list.d/docker.list
		$APT update
		$APT install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
	fi
	cat > /etc/docker/daemon.json <<-EOF
		{"log-driver": "json-file", "log-opts": {"max-size": "10m", "max-file": "3"}}
	EOF
	systemctl restart docker
	usermod -aG docker "$UTENTE"

	# Building the interface needs memory: 4 GB of swap.
	if [ ! -e /swapfile ]; then
		fallocate -l 4G /swapfile
		chmod 600 /swapfile
		mkswap /swapfile >/dev/null
		swapon /swapfile
		echo "/swapfile none swap sw 0 0" >> /etc/fstab
	fi
	echo "Fatto: utente $UTENTE con le chiavi di root, firewall, aggiornamenti automatici, Docker."
	echo "Ora, dal Mac: ssh $UTENTE@<server> sudo true   e poi: sh prepara-server.sh chiudi"
}

chiudi() {
	[ -s "/home/$UTENTE/.ssh/authorized_keys" ] || { echo "Prima: sh prepara-server.sh utente"; exit 1; }
	cat > /etc/ssh/sshd_config.d/10-atlante.conf <<-EOF
		# Atlante: technical access only with personal keys (docs/regole/sicurezza.md, level 2)
		PermitRootLogin no
		PasswordAuthentication no
		KbdInteractiveAuthentication no
		PubkeyAuthentication yes
		AllowUsers $UTENTE
	EOF
	sshd -t
	systemctl reload ssh 2>/dev/null || true  # Ubuntu 24.04 may start ssh on demand: new logins read it anyway
	echo "SSH chiuso: solo l'utente $UTENTE, solo con la chiave."
}

case "${1:-}" in
	utente) utente ;;
	chiudi) chiudi ;;
	*) echo "Uso: sh prepara-server.sh utente | chiudi"; exit 1 ;;
esac
