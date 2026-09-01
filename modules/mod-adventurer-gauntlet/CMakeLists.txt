AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/AdventurerGauntlet.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/GauntletPermadeath.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/GauntletScaling.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/RunReconnect.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/AccountBank.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/AccountCollection.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/KhadgarCelebration.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/CuratedRewards.cpp")
AC_ADD_SCRIPT("${CMAKE_CURRENT_LIST_DIR}/src/SetBonuses.cpp")
AC_ADD_SCRIPT_LOADER("AdventurerGauntlet" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletPermadeath" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletScaling" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletRunReconnect" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletAccountBank" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletAccountCollection" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletCelebration" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletCuratedRewards" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")
AC_ADD_SCRIPT_LOADER("AdventurerGauntletSets" "${CMAKE_CURRENT_LIST_DIR}/src/loader.h")

AC_ADD_CONFIG_FILE("${CMAKE_CURRENT_LIST_DIR}/conf/mod-adventurer-gauntlet.conf.dist")

set(ADVENTURER_GAUNTLET_FINAL_SPELL_PATCHER
    "${CMAKE_CURRENT_LIST_DIR}/tools/patch_installed_spell_dbc.py")
set(ADVENTURER_GAUNTLET_SERVER_DATA_HINT
    "${CMAKE_CURRENT_LIST_DIR}/.server-data-dir")

if(EXISTS "${ADVENTURER_GAUNTLET_SERVER_DATA_HINT}")
    file(READ "${ADVENTURER_GAUNTLET_SERVER_DATA_HINT}" ADVENTURER_GAUNTLET_SERVER_DATA_DIR)
    string(STRIP "${ADVENTURER_GAUNTLET_SERVER_DATA_DIR}" ADVENTURER_GAUNTLET_SERVER_DATA_DIR)
else()
    set(ADVENTURER_GAUNTLET_SERVER_DATA_DIR "${CMAKE_INSTALL_PREFIX}/data")
endif()

set(ADVENTURER_GAUNTLET_FINAL_SPELL_DBC
    "${ADVENTURER_GAUNTLET_SERVER_DATA_DIR}/dbc/Spell.dbc")

install(CODE "
    set(_gauntlet_spell_dbc \"${ADVENTURER_GAUNTLET_FINAL_SPELL_DBC}\")
    set(_gauntlet_spell_patcher \"${ADVENTURER_GAUNTLET_FINAL_SPELL_PATCHER}\")
    if(NOT EXISTS \"\${_gauntlet_spell_dbc}\")
        message(FATAL_ERROR \"Gauntlet final Spell.dbc not found at pinned runtime path: \${_gauntlet_spell_dbc}\")
    endif()
    if(NOT EXISTS \"\${_gauntlet_spell_patcher}\")
        message(FATAL_ERROR \"Gauntlet final Spell.dbc patcher not found: \${_gauntlet_spell_patcher}\")
    endif()
    execute_process(
        COMMAND python3 \"\${_gauntlet_spell_patcher}\" \"\${_gauntlet_spell_dbc}\"
        RESULT_VARIABLE _gauntlet_patch_result
    )
    if(NOT _gauntlet_patch_result EQUAL 0)
        message(FATAL_ERROR \"Gauntlet failed to patch pinned runtime Spell.dbc\")
    endif()
")
