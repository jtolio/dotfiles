case $- in
    *i*) ;;
      *) return;;
esac

HISTCONTROL=ignoreboth

shopt -s histappend

HISTSIZE=10000000000
HISTFILESIZE=1000000000000

shopt -s checkwinsize
shopt -s cmdhist
shopt -u progcomp

shopt -s globstar

[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
    # We have color support; assume it's compliant with Ecma-48
    # (ISO/IEC-6429). (Lack of such support is extremely rare, and such
    # a case would tend to support setf rather than setaf.)
    color_prompt=yes
else
    color_prompt=
fi

if [ "$color_prompt" = yes ]; then
    NONE="\[\033[0m\]"    # unsets color to term's fg color
    K="\[\033[0;30m\]"    # black
    R="\[\033[0;31m\]"    # red
    G="\[\033[0;32m\]"    # green
    Y="\[\033[0;33m\]"    # yellow
    B="\[\033[0;34m\]"    # blue
    M="\[\033[0;35m\]"    # magenta
    C="\[\033[0;36m\]"    # cyan
    W="\[\033[0;37m\]"    # white
    EMK="\[\033[1;30m\]"
    EMR="\[\033[1;31m\]"
    EMG="\[\033[1;32m\]"
    EMY="\[\033[1;33m\]"
    EMB="\[\033[1;34m\]"
    EMM="\[\033[1;35m\]"
    EMC="\[\033[1;36m\]"
    EMW="\[\033[1;37m\]"
    BGK="\[\033[40m\]"
    BGR="\[\033[41m\]"
    BGG="\[\033[42m\]"
    BGY="\[\033[43m\]"
    BGB="\[\033[44m\]"
    BGM="\[\033[45m\]"
    BGC="\[\033[46m\]"
    BGW="\[\033[47m\]"
else
    NONE=""
    K=""
    R=""
    G=""
    Y=""
    B=""
    M=""
    C=""
    W=""
    EMK=""
    EMR=""
    EMG=""
    EMY=""
    EMB=""
    EMM=""
    EMC=""
    EMW=""
    BGK=""
    BGR=""
    BGG=""
    BGY=""
    BGB=""
    BGM=""
    BGC=""
    BGW=""
fi

jt_go_path() {
  local dir="$PWD"
  while true; do
    if [ -f "$dir/.gopath" ]; then
      ( cd "$dir";
        if [ "$(cat .gopath)" != "" ]; then
          cd "$(cat .gopath)";
          echo "$PWD"; 
	fi; )
      return
    fi
    if [ -d "$dir/src" ]; then
      echo "$dir"
      return
    fi
    if [ "$dir" == "/" ]; then
      echo "$PWD"
      return
    fi
    dir="$(dirname "$dir")"
  done
}

jt_in_git() {
  local dir="$PWD"
  while true; do
    if [ -d "$dir/.git" ]; then
      echo "yes"
      return
    fi
    if [ "$dir" == "/" ]; then
      echo "no"
      return
    fi
    dir="$(dirname "$dir")"
  done
}

jt_git_prompt() {
        if [ "$(jt_in_git)" != "yes" ]; then return; fi
        local g="$(git rev-parse --git-dir 2>/dev/null)"
        if [ -n "$g" ]; then
                local r
                local b
                if [ -d "$g/../.dotest" ]
                then
                        if test -f "$g/../.dotest/rebasing"
                        then
                                r="|REBASE"
                        elif test -f "$g/../.dotest/applying"
                        then
                                r="|AM"
                        else
                                r="|AM/REBASE"
                        fi
                        b="$(git symbolic-ref HEAD 2>/dev/null)"
                elif [ -f "$g/.dotest-merge/interactive" ]
                then
                        r="|REBASE-i"
                        b="$(cat "$g/.dotest-merge/head-name")"
                elif [ -d "$g/.dotest-merge" ]
                then
                        r="|REBASE-m"
                        b="$(cat "$g/.dotest-merge/head-name")"
                elif [ -f "$g/MERGE_HEAD" ]
                then
                        r="|MERGING"
                        b="$(git symbolic-ref HEAD 2>/dev/null)"
                else
                        if [ -f "$g/BISECT_LOG" ]
                        then
                                r="|BISECTING"
                        fi
                        if ! b="$(git symbolic-ref HEAD 2>/dev/null)"
                        then
                                if ! b="$(git describe --exact-match HEAD 2>/dev/null)"
                                then
                                        b="$(cut -c1-7 "$g/HEAD")..."
                                fi
                        fi
                fi

        local state
        local git_status="$(git status 2> /dev/null)"

        local remote
        local ahead_pattern="Your branch is ahead of .* by ([0-9]+) commit."
        local behind_pattern="Your branch is behind .* by ([0-9]+) commit."
        local diverge_pattern="diverged.*and have ([0-9]+) and ([0-9]+) different"
        if [[ ${git_status} =~ ${ahead_pattern} ]]; then
            remote="${M}>${BASH_REMATCH[1]}"
        elif [[ ${git_status} =~ ${behind_pattern} ]]; then
            remote="${Y}<${BASH_REMATCH[1]}"
        elif [[ ${git_status} =~ ${diverge_pattern} ]]; then
            remote="${M}>${BASH_REMATCH[1]}${Y}<${BASH_REMATCH[2]}"
        fi

        if [[ ! ${git_status} =~ "working directory clean" ]] && [[ ! ${git_status} =~ "working tree clean" ]]; then
            state="${R}!"
        fi

        echo " $C${b##refs/heads/}$r$remote$state${NONE}"
        fi
}

if [ -z "${debian_chroot:-}" ] && [ -r /etc/debian_chroot ]; then
    debian_chroot=$(cat /etc/debian_chroot)
fi

jt_pwd() {
    history -a
    echo -ne "\033]0;${USER}@${HOSTNAME}: ${PWD}\007"
    case "$USER" in
    jtolds)
        USERP=""
        ;;
    jt)
        USERP=""
        ;;
    *)
        USERP="$EMG$USER$NONE:"
        ;;
    esac
    PS1="$R${debian_chroot:+($debian_chroot)}$NONE$USERP$EMB\w$(jt_git_prompt)$NONE\$ "
    PS2=""
    PS1="\[\e]0;${debian_chroot:+($debian_chroot)}\u@\h: \w\a\]$PS1"
    #export GOPATH="$(jt_go_path)"
}

case "$TERM" in
xterm*|rxvt*)
    PROMPT_COMMAND=jt_pwd
    ;;
*)
    ;;
esac

if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias rm='rm -i'
    alias mv='mv -i'
    alias cp='cp -i'
    alias grep='grep --color=auto'
fi

export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# enable programmable completion features (you don't need to enable
# this, if it's already enabled in /etc/bash.bashrc and /etc/profile
# sources /etc/bash.bashrc).
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

export DEBEMAIL=hello@jtolds.com
export DEBFULLNAME="JT Olds"

if [ -f "$HOME/localbin/bashrc" ]; then
  . "$HOME/localbin/bashrc"
fi
