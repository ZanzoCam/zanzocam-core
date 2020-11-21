##########################################
#
#  SCRIPT DI INSTALLAZIONE RASPI WEBCAM
#
##########################################

echo ""
echo " **********************************************"
echo " ** INIZIO INSTALLAZIONE RASPBERRY PI WEBCAM **"
echo " **********************************************"
echo ""

#<<COMMENT

# Verifica che tutti i comandi siano installati
###############################################

    if ! command -v lsblk > /dev/null; then
        echo " --> ATTENZIONE! lsblk non e' installato. Per favore, installalo con 'sudo apt-get install lsblk' e riprova."
        exit 2
    fi	
    if ! command -v dd > /dev/null; then
        echo " --> ATTENZIONE! dd non e' installato. Per favore, installalo con 'sudo apt-get install dd' e riprova."
        exit 2
    fi	
    if ! command -v git > /dev/null; then
        echo " --> ATTENZIONE! git non e' installato. Per favore, installalo con 'sudo apt-get install git' e riprova."
        exit 2
    fi	
    if ! command -v sshfs > /dev/null; then
        echo " --> ATTENZIONE! sshfs non e' installato. Per favore, installalo con 'sudo apt-get install sshfs' e riprova."
        exit 2
    fi	
    
    
# Raccoglie i dati
################## 
    echo ""
    echo " * STEP 1: Raccolta dei dati"
    echo ""
    
    # Posizione di questo script nel sistema    
    setup_dir="$(dirname "$(readlink -f "$0")")"
    # Per il pattern-matching
    shopt -s extglob
    
    # Dati della rete
    while true; do
        read -p " - Scrivi il nome della rete WiFi (il suo SSID): " ssid
        read -p " - Scrivi la password della rete WiFi: " password
        read -p "   Confermi i dati inseriti? (Si/No) " conferma
        case $conferma in
            SI|si|Si|S|s ) echo ""
                           break;;
            * ) echo "" ;;
        esac
    done
    
    # Dati del server
    while true; do
        echo " - Inserisci l'indirizzo del server dove vuoi ricevere le foto, completo fino al nome della cartella dove hai caricato lo script PHP (esempio: http://example.com/uploads/photos): " 
        read -p " -> " server
        read -p "   Confermi che l'indirizzo del server e' $server ? (Si/No) " conferma
        case $conferma in
            SI|si|Si|S|s ) echo ""
                           break;;
            * ) echo "Ok, riprova." ;;
        esac
    done
    
    # Disco da formattare
    while true; do
        while true; do

            lsblk -p
            echo ""
            echo "Qua sopra dovresti vedere la lista dei dispositivi presenti sul sistema. "
            echo "Una volta identificata la schedina SD, inserisci il nome del dispositivo, per esempio, '/dev/sdx'. "
            echo "Il nome deve finire con una LETTERA, non con un numero! Quindi, /dev/sdc1 e' sbagliato, mentre /dev/sdc e' corretto."
            echo ""
    
            read -p " -> Nome del dispositivo: " nome_dispositivo
 
            case $nome_dispositivo in
             /dev/*[a-z] ) echo "Il nome del dispositivo e' $nome_dispositivo"
                           echo ""
                           break;;

             * ) echo "Il nome del dispositivo non e' corretto. Riprova."
                 echo "" ;;
            esac
        done
        
        # Conferma il dispositivo  
        echo "ATTENZIONE: il dispositivo $nome_dispositivo sta per essere FORMATTATO."
        echo "Questa operazione distruggera' tutti i dati all'interno del dispositivo."
        echo "Sei SICURO/A che $nome_dispositivo e' il dispositivo giusto?"
        echo ""
        
        read -p " -> Scrivi SI per FORMATTARE $nome_dispositivo: " conferma
        case $conferma in
            SI|si|Si ) break;;
            * ) echo "Non hai confermato il nome del dispositivo."
                echo "" ;;
        esac
    done
    echo ""
    echo "   ******************* "
    

    echo ""
    echo " * STEP 2: Setup del Raspberry Pi"
    echo ""

    # Scarica la distro
    echo " - Download del sistema operativo (Raspberry Pi OS)"
    echo ""
    echo "In totale circa 1GB, assicurati di avere abbastanza spazio sul disco."
    echo "Se necessario, puoi interrompere il download: la prossima volta non ripartira' da zero."
    
    wget -c https://downloads.raspberrypi.org/raspios_lite_armhf_latest -q --show-progress
    cp raspios_lite_armhf_latest raspios_lite_armhf_latest.zip
    
    echo "Download completato."
    echo "Unzipping..."
    
    unzip raspios_lite_armhf_latest.zip
    mv $(unzip -Z1 raspios_lite_armhf_latest.zip) raspios.img
    
    echo "File dezippato."
    echo ""
    
    # Formatta la scheda
    echo " - Installazione del sistema operativo sulla schedina SD."
    echo ""
    echo "Formattazione in corso..."
    sudo dd bs=4M if=raspios.img of=$nome_dispositivo status=progress oflag=direct
    sync
    echo "Formattazione di $nome_dispositivo completata"
    echo ""
    

    # Aggiungi il file di configurazione 
    echo " - Mount di ${nome_dispositivo}1 (boot) sotto /mnt/raspberry1"
    sudo mkdir -p /mnt/raspberry1
    
    if ! sudo mount ${nome_dispositivo}1 /mnt/raspberry1; then
        echo ""
        echo " ====> ERRORE!! <==== "
        echo "Non e' stato possibile montare la partizione $nome_dispositivo1, anche con SUDO. Controlla il messaggio di errore e riprova."
        exit 1
    fi
    
    echo " - Creazione del file 'ssh' nella partizione di boot per abilitare SSH"
    sudo touch /mnt/raspberry1/ssh
    if ! test -f "/mnt/raspberry1/ssh"; then
        echo ""
        echo " ====> ERRORE!! <==== "
        echo "Non e' stato possibile creare il file 'ssh' sul disco. "
        echo "Ricordati, prima di estratte la SD, di montarla come un dispositivo normale e, nella partizione chiamata 'boot', creare un file vuoto, senza estensione, chiamato 'ssh'. Se ti dimentichi, il Raspberry non attivera' SSH all'avvio e sara' irraggiungibile."
        echo ""
    fi
    
    echo " - Aggiornamento di /boot/config.txt"
    sudo cp "$setup_dir/config.txt" /mnt/raspberry1/config.txt
    
    echo " - Unmount di ${nome_dispositivo}1"
    sudo umount ${nome_dispositivo}1
    sudo rm -r /mnt/raspberry1
    
    echo " - Mount di ${nome_dispositivo}2 (rootfs) sotto /mnt/raspberry2"
    sudo mkdir -p /mnt/raspberry2
    
    if ! sudo mount ${nome_dispositivo}2 /mnt/raspberry2; then
        echo ""
        echo " ====> ERRORE!! <==== "
        echo "Non e' stato possibile montare la partizione $nome_dispositivo2, anche con SUDO. Controlla il messaggio di errore e riprova."
        exit 1
    fi
    
    echo " - Aggiornamento di .bashrc in /home/pi"
    sudo cat "$setup_dir/bashrc" | sudo tee /mnt/raspberry2/home/pi/.bashrc > /dev/null 
    
    #echo " - Aggiornamento di rc.local in /etc"
    #sudo cat "$setup_dir/rc.local" | sudo tee -a /mnt/raspberry2/etc/rc.local > /dev/null 
    
    echo " - Copia di onboard_setup.sh in /home/pi"
    sudo cp "$setup_dir/onboard_setup.sh" /mnt/raspberry2/home/pi/onboard_setup.sh
    
    echo " - Installazione del software della webcam in /home/pi"
    sudo mkdir -p /mnt/raspberry2/home/pi/webcam/
    sudo cp $setup_dir/../pi/* /mnt/raspberry2/home/pi/webcam/
    sudo chmod +x /mnt/raspberry2/home/pi/onboard_setup.sh    
    sudo awk '{if($2=="SERVER_ADDRESS") {$2=$server} print $0}' /mnt/raspberry2/home/pi/webcam/configurazione.json > /dev/null
    echo ""
    
    # Configurazione WiFi
    echo " - Configurazione rete WiFi."
    echo 'ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="'$ssid'"
    psk="'$password'"
}
' | sudo tee /mnt/raspberry2/etc/wpa_supplicant/wpa_supplicant.conf > /dev/null
    
    echo " - Unmount di ${nome_dispositivo}2"
    sudo umount ${nome_dispositivo}2
    sudo rm -r /mnt/raspberry2
    echo ""
    echo "   ******************* "

# Verifica dell'installazione
#############################
    echo ""
    echo " * STEP 3: Avvio del Raspberry Pi"
    echo ""
    echo "La scheda SD e' completamente configurata."
    echo ""
    echo "Espelli la SD se e' ancora montata, rimuovila e inseriscila di nuovo nel PC. Dovresti vedere due partizioni, 'boot' e 'rootfs'. Controlla che dentro 'boot' ci sia un file chiamato 'ssh' (senza estensione) e che il contenuto di 'rootfs' assomigli al contenuto di / sul tuo computer."
    echo "Se tutto e' in ordine, smonta le partizioni, rimuovi la schedina, inseriscila nel Raspberry Pi e accendilo. "
    echo ""
    read -p "Premi qualunque tasto per continuare "
    echo ""
    echo "   ******************* "
    echo ""
    echo " * STEP 4: Connessione."
    echo ""
    echo "Qua sotto dovrebbe apparire una riga con alcuni dati, tra cui l'indirizzo IP del Raspberry. Ignora gli IP di altri dispositivi."
    echo "Ci vuole qualche secondo..."
    while true; do
        echo "--------------------------------------------"
        nmap -sn 192.168.1,2.0/24 | grep "Nmap scan" | sed "s/Nmap scan report for/ - /g"
        echo "--------------------------------------------"
        echo "Vedi l'indirizzo IP del Raspberry? Se SI, copialo qua. Se NO, aspetta qualche minuto e poi digita NO. L'inizializzazione puo' essere lunga, quindi abbi pazienza."
        read -p "-> " indirizzo_ip
        case $indirizzo_ip in
           No|NO|no|N|n ) echo "";;
           * ) read -p "Confermi che l'indirizzo IP e' $indirizzo_ip ? (Si/No) " conferma
               case $conferma in
                    SI|si|Si|S|s ) break;;
                    * ) echo "Ok, riprova." ;;
               esac
        esac
    done
    echo " -> Prima connessione SSH con il Raspberry: la password e' 'raspberry'. Il sistema installera' automaticamente alcuni pacchetti e poi si disconnettera'."
    read -p "Premi qualunque tasto per continuare "
    echo ""
    echo "   ******************* "
    echo ""
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "pi@$indirizzo_ip"
        
    echo ""
    echo "   ******************* "
    echo ""
    read -p "Aspetta che il Pi finisca il reboot (il led diventa stabile) e poi premi qualunque tasto per continuare."
    echo ""
    echo "Seconda connessione al Raspberry: ti verra' chiesto di impostare una nuova password."
    echo ""
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "pi@$indirizzo_ip"
    
    echo ""
    echo " *********** CONFIGURAZIONE COMPLETATA **************"
    echo ""
    echo "La scheda e' configurata per inviare una foto e leggere il nuovo file di configurazione sul server ogni 5 minuti."
        echo "Ora configura il server per ricevere le foto e modificare le impostazioni della scheda."
    
    echo ""
    echo "   ******************* "

