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


# Scrivi sulla SD
##################
    echo " * STEP 2: Installazione del sistema operativo sulla schedina SD."
    echo ""

    lsblk -p

    echo "Qua sopra dovresti vedere la lista dei dispositivi presenti sul sistema. "
    echo "Una volta identificata la schedina SD, inserisci il nome del dispositivo, per esempio, '/dev/sdx'. "
    echo "Il nome deve finire con una LETTERA, non con un numero! Quindi, /dev/sdc1 e' sbagliato, mentre /dev/sdc e' corretto."
    echo ""

    # Ottiene il nome del dispositivo
    while true   # Loop per la conferma
        while true   # loop per il nome
        
            shopt -s extglob
            do
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
        
        do
          read -p " -> Scrivi SI per FORMATTARE $nome_dispositivo: " conferma
          case $conferma in
           SI|si|Si ) break;;
           * ) echo "Non hai confermato il nome del dispositivo."
               echo "" ;;
          esac
        done
        
    echo ""
    echo "Formattazione in corso:"
    echo " - Unmount di tutte le partizioni di $nome_dispositivo ..."
    umount $nome_dispositivo
    echo " - Copia dei files..."
    sudo dd bs=4M if=raspios.img of=$nome_dispositivo status=progress oflag=direct
    sync
    echo "Formattazione di $nome_dispositivo completata"
    
COMMENT
nome_dispositivo=/dev/sda 


# Aggiungi il file di configurazione 
####################################
    echo ""
    echo " * STEP 3: Preparazione dei files di configurazione"
    echo ""
    echo " - Mount di $nome_dispositivo sotto /mnt/raspberry"
    sudo mkdir /mnt/raspberry
    sudo mount ${nome_dispositivo}2 /mnt/raspberry
    
    echo " - Aggiornamento di /boot/config.txt"
    echo "
# Disable the rainbow splash screen
disable_splash=1

# No boot delay
boot_delay=0

# Disable the LED
dtparam=act_led_trigger=none
dtparam=act_led_activelow=on

start_x=1
gpu_mem=128
" | sudo tee -a > /mnt/raspberry/boot/config.txt > /dev/null
    
    echo " - Aggiornamento di /etc/rc.local"
    echo '
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.

# Disable the HDMI port (to save power)
/usr/bin/tvservice -o

# Print the IP address
_IP=$(hostname -I) || true
if [ "$_IP" ]; then
  printf "My IP address is %s\n" "$_IP"
fi

exit 0
' | sudo tee -a >  /mnt/raspberry/etc/rc.local > /dev/null
    echo "    ok"
    echo ""
    

# Configurazione WiFi
#####################
    echo " * STEP 4: COnfigurazione rete WiFi."
    echo ""
    do
        do
            read -p " - Scrivi il nome della rete WiFi (il suo SSID): " ssid
            read -p " - Scrivi la password della rete WiFi): " password
            read -p "   Confermi i dati inseriti? (Si/No)" conferma
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
' | sudo tee -a >  /etc/wpa_supplicant/wpa_supplicant.conf > /dev/null
        echo "Rete WiFi configurata."
        echo "Test della rete (ping a Google: richiede 5 secondi)"
        echo "-------------------------------------"
        ping -w 5www.google.com
        echo "-------------------------------------"
        read -p "Il ping ha funzionato? (Si/No)" conferma
        case $conferma in
           SI|si|Si|S|s ) break;;
           * ) echo "Prova a reinserire i dati della rete Wifi" 
               echo "";;
        esac
    done

# Installa il software per la webcam
####################################
    echo " * STEP 5: Installazione del software per la webcam"
    echo ""


# Verifica dell'installazione
#############################
    echo ""
    echo " * STEP 6: Avvio del Raspberry Pi"
    umount ${nome_dispositivo}2
    sudo rm -r /mnt/raspberry
    echo ""
    echo "La scheda SD e' completamente configurata."
    echo "Inseriscila nel Raspberry Pi, accendilo e aspetta qualche secondo."
    echo ""
    echo " * STEP 7: Connessione."
    echo "Prima di tutto e' necessario trovare l'IP del Raspberry Pi."
    echo "Qua sotto dovrebbe apparire una riga con alcuni dati, tra cui un indirizzo IP."
    do
        echo "--------------------------------------------"
        arp -a | grep -i "b8:27:eb\|dc:a6:32"
        echo "--------------------------------------------"
        read -p "Vedi l'indirizzo IP qua sopra? Se NO, aspetta qualche secondo e poi digita NO (Si/No)" conferma
        case $conferma in
           SI|si|Si|S|s ) 
               read -p "Per favore, copialo qua: " indirizzo_ip
               echo "Confermi che l'indirizzo IP e' " $indirizzo_ip "? (Si/No)"
               case $conferma in
                    SI|si|Si|S|s ) break;;
                    * ) echo "Ok, riprova."
           * ) echo "";;
        esac
    done
    echo "Connessione SSH con il Raspberry: digita 'raspberry' nel campo della password."
    ssh pi@${indirizzo_ip}


# Connettiti

# Scatta una foto di prova
