using UnityEngine;
using UnityEngine.UI;

public class PauseManager : MonoBehaviour
{
    public GameObject pauseMenuUI; // Duraklatma menüsü referansý
    private bool isPaused = false; // Oyunun duraklatýlmýþ olup olmadýðýný takip eden deðiþken

    private void Start()
    {
        // Oyuna baþladýðýnda fareyi gizle ve kilitle
        Cursor.visible = false;
        Cursor.lockState = CursorLockMode.Locked;

        Resume();
    }

    void Update()
    {
        // ESC tuþuna basýldýðýnda oyunu duraklatma veya devam ettirme
        if (Input.GetKeyDown(KeyCode.Escape))
        {
            if (isPaused)
            {
                Resume();
            }
            else
            {
                Pause();
            }
        }
    }

    public void Resume()
    {
        pauseMenuUI.SetActive(false); // Duraklatma menüsünü gizle
        Time.timeScale = 1f; // Oyunu devam ettir

        isPaused = false;
        // Ýmleci Kilitle
        Cursor.visible = false;
        Cursor.lockState = CursorLockMode.Locked;
    }

    void Pause()
    {
        pauseMenuUI.SetActive(true); // Duraklatma menüsünü göster
        Time.timeScale = 0f; // Oyunu duraklat
        isPaused = true;

        // Ýmleci göster ve serbest býrak
        Cursor.visible = true;
        Cursor.lockState = CursorLockMode.None;
    }
}
