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

<<COMMENT

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
    

# Scarica la distro
####################
    echo " * STEP 1: Download del sistema operativo (Raspberry Pi OS)"
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
    echo "   ******************* "
    

# Scrivi sulla SD
##################
    echo ""
    echo " * STEP 2: Installazione del sistema operativo sulla schedina SD."
    echo ""

    # Ottiene il nome del dispositivo
    while true; do   # Loop per la conferma
        while true; do   # loop per il nome

            lsblk -p

            echo "Qua sopra dovresti vedere la lista dei dispositivi presenti sul sistema. "
            echo "Una volta identificata la schedina SD, inserisci il nome del dispositivo, per esempio, '/dev/sdx'. "
            echo "Il nome deve finire con una LETTERA, non con un numero! Quindi, /dev/sdc1 e' sbagliato, mentre /dev/sdc e' corretto."
            echo ""
    
            shopt -s extglob  # Per il pattern-matching
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
    echo "Formattazione in corso:"
    echo " - Copia dei files..."
    sudo dd bs=4M if=raspios.img of=$nome_dispositivo status=progress oflag=direct
    sync
    echo "Formattazione di $nome_dispositivo completata"
    echo ""
    echo "   ******************* "
    
    
COMMENT
nome_dispositivo=/dev/sda 


# Aggiungi il file di configurazione 
####################################

    echo ""
    echo " * STEP 3: Copia dei files di configurazione e della webcam."
    echo ""
    
    # Posizione di questo script nel sistema    
    setup_dir="$(dirname "$(readlink -f "$0")")"
    
    echo " - Mount di ${nome_dispositivo}1 (boot) sotto /mnt/raspberry1"
    sudo mkdir -p /mnt/raspberry1
    
    if ! sudo mount ${nome_dispositivo}1 /mnt/raspberry1; then
        echo ""
        echo " ====> ERRORE!! <==== "
        echo "Non e' stato possibile montare la partizione $nome_dispositivo1, anche con SUDO. Controlla il messaggio di errore e riprova."
        exit 1
    fi
    
    echo " - Creazione del file 'ssh' nella partizione di boot per abilitare SSH"
    sudo touch "/mnt/raspberry1/ssh"
    
    echo " - Unmount di ${nome_dispositivo}1"
    sudo umount ${nome_dispositivo}1
    sudo rm -r /mnt/raspberry1
    echo ""
    
    echo " - Mount di ${nome_dispositivo}2 (rootfs) sotto /mnt/raspberry2"
    sudo mkdir -p /mnt/raspberry2
    
    if ! sudo mount ${nome_dispositivo}2 /mnt/raspberry2; then
        echo ""
        echo " ====> ERRORE!! <==== "
        echo "Non e' stato possibile montare la partizione $nome_dispositivo2, anche con SUDO. Controlla il messaggio di errore e riprova."
        exit 1
    fi
    
    echo " - Aggiornamento di /boot/config.txt"
    sudo cp "$setup_dir/config.txt" /mnt/raspberry2/boot/config.txt
    
    echo " - Aggiornamento di /etc/rc.local"
    sudo  cp "$setup_dir/rc.local" /mnt/raspberry2/etc/rc.local
    
    echo " - Copia di onboard_setup.sh in /home/pi"
    sudo  cp "$setup_dir/onboard_setup.sh" /mnt/raspberry2/home/pi/onboard_setup.sh
    
    echo " - Installazione del software della webcam in /home/pi"
     while true; do
        read -p "-> Inserisci l'indirizzo del server dove vuoi ricevere le foto, completo fino al nome della cartella dove hai caricato lo script PHP (esempio: http://example.com/uploads/photos): " server
        read -p "Confermi che l'indirizzo del server e' $server ? (Si/No) " conferma
        case $conferma in
            SI|si|Si|S|s ) break;;
            * ) echo "Ok, riprova." ;;
        esac
    done
    git clone -q https://github.com/ZanSara/remotecam.git .temporary_folder_webcam > /dev/null
    sudo mkdir -p /mnt/raspberry2/home/pi/webcam/
    sudo cp .temporary_folder_webcam/pi/* /mnt/raspberry2/home/pi/webcam/
    sudo awk '{if($2=="SERVER_ADDRESS") {$2=$server} print $0}' /mnt/raspberry2/home/pi/webcam/configurazione.json > /dev/null
    sudo rm -rf .temporary_folder_webcam/
    echo ""
    echo "   ******************* "
    

# Configurazione WiFi
#####################
    echo ""
    echo " * STEP 4: Configurazione rete WiFi."
    echo ""
    while true; do
        read -p " - Scrivi il nome della rete WiFi (il suo SSID): " ssid
        read -p " - Scrivi la password della rete WiFi): " password
        read -p "   Confermi i dati inseriti? (Si/No) " conferma
        case $conferma in
            SI|si|Si|S|s ) break;;
            * ) echo "" ;;
        esac
    done
    
    echo '
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=fr
    
    
network={
ssid="'$ssid'"
psk="'$password'"
}
' | sudo tee -a /mnt/raspberry2/etc/wpa_supplicant/wpa_supplicant.conf > /dev/null
    echo "   Rete WiFi configurata."
    echo ""
    
    echo " - Unmount di ${nome_dispositivo}2"
    sudo umount ${nome_dispositivo}2
    sudo rm -r /mnt/raspberry2
    echo ""
    echo "   ******************* "

#COMMENT

# Verifica dell'installazione
#############################
    echo ""
    echo " * STEP 5: Avvio del Raspberry Pi"
    echo ""
    echo "La scheda SD e' completamente configurata."
    echo "Inseriscila nel Raspberry Pi e accendilo. Un ulteriore step di configurazione avviene alla prima accensione, ma non e' necessario alcun intervento."
    echo ""
    read -p "Premi qualunque tasto per continuare "
    echo ""
    echo "   ******************* "
    echo ""
    echo " * STEP 6: Connessione."
    echo ""
    echo "Qua sotto dovrebbe apparire una riga con alcuni dati, tra cui l'indirizzo IP della scheda."
    while true; do
        echo "--------------------------------------------"
        arp -a | grep -i "b8:27:eb\|dc:a6:32"
        echo "--------------------------------------------"
        echo "Vedi l'indirizzo IP qua sopra? Se SI, copialo qua. Se NO, aspetta qualche secondo e poi digita NO."
        read -p "-> " indirizzo_ip
        case $indirizzo_ip in
           No|NO|no|N|n ) echo "Ok, riprova."
                          echo "";;
           * ) read -p "Confermi che l'indirizzo IP e' $indirizzo_ip ? (Si/No) " conferma
               case $conferma in
                    SI|si|Si|S|s ) break;;
                    * ) echo "Ok, riprova." ;;
               esac
        esac
    done
    echo "Connessione SSH con il Raspberry: ti verra' chiesto di impostare una nuova password."
    echo ""
    sudo ssh "pi@$indirizzo_ip"
    sudo mkdir -p /mnt/raspberry
    
    sudo sshfs "pi@$indirizzo_ip":/home/pi /mnt/raspberry
    
    if test -f "/mnt/raspberry/onboard_setup.sh"; then
        echo ""
        echo " ==> ATTENZIONE! <=="
        echo " Il setup iniziale non e' stato completato: 'onboard_setup.sh' non e' stato cancellato. "
        echo " Potrebbero essersi verificati degli errori durante l'avvio."
    else
        echo ""
        echo "Sembra che tutto sia in ordine. La scheda e' confiugurata per inviare una foto e leggere il nuovo file di configurazione sul server ogni 5 minuti."
        echo "Ora configura il server per ricevere le foto e modificare le impostazioni della scheda."
    fi
    
    echo ""
    echo "   ******************* "



# Connettiti

# Scatta una foto di prova
