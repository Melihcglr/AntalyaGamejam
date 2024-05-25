using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class NightLight : MonoBehaviour
{
    public Light[] lights; // Kontrol edilecek ýþýklar
    public float nightStartTime = 20f; // Gece baþlama saati (20:00)
    public float nightEndTime = 6f; // Gece bitiþ saati (06:00)

    private Sun sun; // Güneþ script'inden saati almak için referans

    void Start()
    {
        // Güneþ script'ine referans al
        sun = FindObjectOfType<Sun>();
        UpdateLights();
    }

    void Update()
    {
        UpdateLights();
    }

    void UpdateLights()
    {
        float currentTime = sun.time * 24f; // Güneþ script'inden saati al (0-1 arasý deðeri 0-24 saat aralýðýna çevir)

        if (IsNightTime(currentTime))
        {
            SetLights(true); // Gece ýþýklarý aç
        }
        else
        {
            SetLights(false); // Gündüz ýþýklarý kapat
        }
    }

    bool IsNightTime(float time)
    {
        // Gece zamaný kontrolü (20:00-24:00 ve 00:00-06:00)
        if (nightStartTime > nightEndTime)
        {
            return time >= nightStartTime || time < nightEndTime;
        }
        else
        {
            return time >= nightStartTime && time < nightEndTime;
        }
    }

    void SetLights(bool state)
    {
        foreach (Light light in lights)
        {
            light.enabled = state;
        }
    }
}
