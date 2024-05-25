using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using TMPro;

public class Sun : MonoBehaviour
{
    [Range(0, 1)] public float time;
    public float startTime;
    public float dayLength;

    private float timeRate;
    public Vector3 noon;

    public TextMeshProUGUI timeText; // TextMeshPro bileþeni referansý

    public float dayDuration = 10f; // Gündüz süresi (dakika)
    public float nightDuration = 10f; // Gece süresi (dakika)

    public float sunriseHour = 6f; // Gün doðumu saati
    public float sunsetHour = 18f; // Gün batýmý saati

    private void Start()
    {
        // Toplam gün uzunluðu
        dayLength = dayDuration + nightDuration;
        timeRate = 1 / (dayLength * 60); // Gün uzunluðunu saniyeye çevir
        time = startTime;
    }

    private void Update()
    {
        time += timeRate * Time.deltaTime;
        if (time > 1)
        {
            time = 0;
        }

        // Gün doðumu ve gün batýmý zamanlarýný 0-1 arasý deðerlere çevir
        float sunriseTime = sunriseHour / 24f;
        float sunsetTime = sunsetHour / 24f;

        // Güneþin dönüþünü ayarlama
        if (time <= sunriseTime || time >= sunsetTime)
        {
            // Gece
            float nightTime = (time >= sunsetTime) ? (time - sunsetTime) / (1f - sunsetTime + sunriseTime) : (time + (1f - sunsetTime)) / (1f - sunsetTime + sunriseTime);
            transform.eulerAngles = Vector3.Lerp(noon, new Vector3(360, 0, 0), nightTime);
        }
        else
        {
            // Gündüz
            float dayTime = (time - sunriseTime) / (sunsetTime - sunriseTime);
            transform.eulerAngles = Vector3.Lerp(Vector3.zero, noon, dayTime);
        }

        UpdateTimeText();
    }

    private void UpdateTimeText()
    {
        // Gün içindeki saati hesapla
        float hours = 24 * time;
        int hoursInt = Mathf.FloorToInt(hours);
        int minutesInt = Mathf.FloorToInt((hours - hoursInt) * 60);

        string timeString = string.Format("{0:00}:{1:00}", hoursInt, minutesInt);
        timeText.text = timeString;
    }
}
