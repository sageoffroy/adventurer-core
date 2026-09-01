AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/AdventurerGauntlet.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/GauntletPermadeath.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/GauntletScaling.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/RunReconnect.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/AccountStash.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/AccountCollection.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/KhadgarCelebration.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/CuratedRewards.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/SetBonuses.cpp")
AC_ADD_SCRIPT_LOADER("AdventurerGauntlet" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletPermadeath" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletScaling" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletRunReconnect" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletAccountStash" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletAccountCollection" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletCelebration" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletCuratedRewards" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletSets" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")

AC_ADD_CONFIG_FILE("${CMAKE_CURRENT_LIST_DIR}/conf/mod-adventurer-gauntlet.conf.dist")

# The helper installer patches the development/runtime DBC before compilation,
# but `make install` can refresh the installed data bundle afterwards. Reapply
# the two Gauntlet auras to the *final* installed Spell.dbc so worldserver sees
# the same IDs that the client does. Lone Wolf clones the already-working pledge
# aura structure instead of introducing a second custom spell format.
set(ADVENTURER_GAUNTLET_FINAL_SPELL_PATCHER
    "${CMAKE_CURRENT_LIST_DIR}/tools/patch_installed_spell_dbc.py")

install(CODE "
    set(_gauntlet_spell_dbc \"\$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/data/dbc/Spell.dbc\")
    set(_gauntlet_spell_patcher \"${ADVENTURER_GAUNTLET_FINAL_SPELL_PATCHER}\")
    if(EXISTS \"\${_gauntlet_spell_dbc}\" AND EXISTS \"\${_gauntlet_spell_patcher}\")
        execute_process(
            COMMAND python3 \"\${_gauntlet_spell_patcher}\" \"\${_gauntlet_spell_dbc}\"
            RESULT_VARIABLE _gauntlet_patch_result
        )
        if(NOT _gauntlet_patch_result EQUAL 0)
            message(FATAL_ERROR \"Gauntlet failed to patch final installed Spell.dbc\")
        endif()
    else()
        message(FATAL_ERROR \"Gauntlet final Spell.dbc patch target or patcher is missing\")
    endif()
")
