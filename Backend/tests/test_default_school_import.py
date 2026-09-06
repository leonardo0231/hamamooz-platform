@pytest.mark.django_db
def test_import_without_school_uses_besat(
    api_client,
    besat_school,
    sample_excel
):

    response = api_client.post(
        "/api/imports/",
        {
            "source_file": sample_excel,
            "import_type":
            "comprehensive_school"
        },
        format="multipart"
    )


    assert response.status_code == 201

    job = ImportJob.objects.first()

    assert job.school == besat_school