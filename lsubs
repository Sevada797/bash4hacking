lsubs () {
    while IFS= read -r sub; do
        if (($(curl https://$sub -sI | head -n 1 | awk '{print $2}')==200)); then echo $sub>>subs200; fi
    done < "$1"

}
